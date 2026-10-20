#!/usr/bin/env python3
"""Stage 3: clone each sampled repository (blobless partial clone) and evaluate the compiled
constraints of every version of its context files against the repository history.

Output: one gzip JSON per repository in <cache>/mined/.
Usage: s3_mine.py [--workers N] [--only owner/repo] [--limit N] [--force]
"""
import argparse, gzip, json, os, subprocess, sys, time, traceback, collections, re
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compiler as K

CACHE = os.path.expanduser(os.environ.get("S03_CACHE", "~/.cache/context-rot-study/S03"))
CLONES, MINED = os.path.join(CACHE, "clones"), os.path.join(CACHE, "mined")
CTX_PATHS = ["AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md"]
BASELINE = "README.md"
MAX_EVEN = 150       # evenly spaced snapshots in addition to version commits and their parents
MAX_VERSIONS = 400
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
AGENT_RX = re.compile(r"claude|copilot|cursor|codex|devin|openhands|aider|gemini|jules|amp@|sourcegraph|\[bot\]", re.I)


def git(d, *args, inp=None, timeout=600, check=True):
    p = subprocess.run(["git", "-C", d, *args], input=inp, capture_output=True, timeout=timeout, env=ENV)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:4])}: {p.stderr.decode(errors='replace')[:300]}")
    return p.stdout.decode("utf-8", errors="replace")


class Repo:
    def __init__(self, d):
        self.d = d
        self.tree_cache = collections.OrderedDict()
        self.blob_cache = {}

    def tree(self, commit):
        """Return (paths list, manifest map path->oid, tracked map path->(mode, oid))."""
        if commit in self.tree_cache:
            self.tree_cache.move_to_end(commit)
            return self.tree_cache[commit]
        out = git(self.d, "ls-tree", "-r", "-z", commit)
        paths, man, tracked = [], {}, {}
        for ent in out.split("\0"):
            if not ent:
                continue
            meta, _, path = ent.partition("\t")
            mode, typ, oid = meta.split(" ")
            path = sys.intern(path)
            if typ == "commit":   # submodule: counts as a directory
                paths.append(path + "/.submodule")
                continue
            paths.append(path)
            if typ == "blob" and mode != "120000" and K.is_manifest(path):
                man[path] = oid
            if path in CTX_PATHS or path == BASELINE:
                tracked[path] = (mode, oid)
        res = (paths, man, tracked)
        self.tree_cache[commit] = res
        if len(self.tree_cache) > 6:
            self.tree_cache.popitem(last=False)
        return res

    def fetch_blobs(self, oids):
        need = [o for o in set(oids) if o not in self.blob_cache]
        if not need:
            return
        # which are missing locally
        chk = subprocess.run(["git", "-C", self.d, "cat-file", "--batch-check"], input="\n".join(need).encode(),
                             capture_output=True, env=dict(ENV, GIT_NO_LAZY_FETCH="1"), timeout=300).stdout.decode()
        missing = [l.split()[0] for l in chk.splitlines() if l.endswith("missing")]
        for i in range(0, len(missing), 2000):
            batch = missing[i:i + 2000]
            subprocess.run(["git", "-C", self.d, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags",
                            "--no-write-fetch-head", "--recurse-submodules=no", "--filter=blob:none", "--stdin"],
                           input="\n".join(batch).encode(), capture_output=True, env=ENV, timeout=900)
        p = subprocess.run(["git", "-C", self.d, "cat-file", "--batch"], input="\n".join(need).encode(),
                           capture_output=True, env=ENV, timeout=900)
        buf, pos = p.stdout, 0
        while pos < len(buf):
            nl = buf.index(b"\n", pos)
            head = buf[pos:nl].decode().split()
            pos = nl + 1
            if len(head) == 3:
                size = int(head[2])
                data = buf[pos:pos + size]
                pos += size + 1
                self.blob_cache[head[0]] = data[:400_000].decode("utf-8", errors="replace")
            else:
                self.blob_cache[head[0]] = ""

    def state(self, commit, prefetch=True):
        paths, man, _ = self.tree(commit)
        if prefetch:
            self.fetch_blobs(man.values())
        return K.RepoState(paths, LazyManifests(self, man))


class LazyManifests:
    def __init__(self, repo, man):
        self.repo, self.man = repo, man

    def items(self):
        self.repo.fetch_blobs(self.man.values())
        return [(p, self.repo.blob_cache.get(o, "")) for p, o in self.man.items()]


def clone(full, d):
    if os.path.isdir(os.path.join(d, ".git")) or os.path.isfile(os.path.join(d, "HEAD")):
        return
    p = subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--single-branch", "--no-tags",
                        f"https://github.com/{full}.git", d], capture_output=True, env=ENV, timeout=900)
    if p.returncode != 0:
        subprocess.run(["rm", "-rf", d])
        raise RuntimeError("clone failed: " + p.stderr.decode(errors="replace")[:300])


def mine(full, meta):
    t_start = time.time()
    d = os.path.join(CLONES, full.replace("/", "__"))
    clone(full, d)
    R = Repo(d)
    # first-parent chain, oldest first
    raw = git(d, "log", "--first-parent", "--format=%H%x09%ct%x09%P%x09%an%x09%s%x09%(trailers:key=Co-authored-by,valueonly,separator=%x3B)", "HEAD")
    chain = []
    for line in raw.splitlines():
        f = line.split("\t")
        if len(f) < 5 or len(f[0]) != 40:
            continue
        chain.append({"h": f[0], "ts": int(f[1]), "merge": len(f[2].split()) > 1, "an": f[3], "s": f[4][:160],
                      "co": f[5][:200] if len(f) > 5 else ""})
    chain.reverse()
    idx_of = {c["h"]: i for i, c in enumerate(chain)}
    head = chain[-1]["h"]
    _, _, tracked_head = R.tree(head)
    files = [p for p in CTX_PATHS + [BASELINE] if p in tracked_head and tracked_head[p][0] != "120000"]
    symlinks = [p for p in CTX_PATHS if p in tracked_head and tracked_head[p][0] == "120000"]
    ctx_files = [p for p in files if p != BASELINE]
    if not ctx_files:
        return {"repo": full, "skip": "no regular root context file at HEAD", "symlinks": symlinks}
    # versions of each tracked file along the first-parent chain
    versions = {}
    for p in files:
        out = git(d, "log", "--first-parent", "--format=%H", "HEAD", "--", p)  # tree comparison only, no blobs needed
        vs = sorted({idx_of[h] for h in out.split() if h in idx_of})
        versions[p] = vs
    t0 = min(versions[p][0] for p in ctx_files if versions[p])
    # snapshot indices
    snaps = set()
    for p in files:
        vs = [v for v in versions[p] if v >= t0]
        if len(vs) > MAX_VERSIONS:
            step = len(vs) / MAX_VERSIONS
            vs = sorted({vs[int(i * step)] for i in range(MAX_VERSIONS)} | {vs[-1]})
        for v in vs:
            snaps.add(v)
            if v - 1 >= t0:
                snaps.add(v - 1)
    n = len(chain) - t0
    if n <= MAX_EVEN:
        snaps |= set(range(t0, len(chain)))
    else:
        snaps |= {t0 + round(i * (n - 1) / (MAX_EVEN - 1)) for i in range(MAX_EVEN)}
    snaps = sorted(snaps)
    # pass 1: blob oids of tracked files and manifests at every snapshot
    file_oid = {p: {} for p in files}
    need = set()
    for s in snaps:
        _, man, tracked = R.tree(chain[s]["h"])
        need |= set(man.values())
        for p in files:
            if p in tracked and tracked[p][0] != "120000":
                file_oid[p][s] = tracked[p][1]
                need.add(tracked[p][1])
    R.fetch_blobs(need)
    compiled = {}

    def constraints_of(oid):
        if oid not in compiled:
            compiled[oid] = K.compile_text(R.blob_cache.get(oid, ""))
        return compiled[oid]

    # pass 2: evaluate
    timeline = {p: {} for p in files}   # key -> dict(meta, obs={snap: code})
    for s in snaps:
        st = None
        for p in files:
            oid = file_oid[p].get(s)
            if oid is None:
                continue
            cs = constraints_of(oid)
            if not cs:
                continue
            if st is None:
                st = R.state(chain[s]["h"])
            for c in cs:
                ok = st.check(c)
                code = 0
                if ok:
                    code = 1 if (c.kind != "path" or st.check(c, strict=True)) else 2
                e = timeline[p].get(c.key)
                if e is None:
                    e = timeline[p][c.key] = {"kind": c.kind, "sub": c.sub, "target": c.target, "line": c.line,
                                              "raw": c.raw, "obs": {}}
                e["obs"][s] = code
    # locate breaks exactly by bisection on the first-parent chain, and classify sync updates
    def live_oid(p, i):
        # blob of file p at chain index i
        _, _, tracked = R.tree(chain[i]["h"])
        return tracked[p][1] if p in tracked and tracked[p][0] != "120000" else None

    def present_and_ok(p, key, i):
        oid = live_oid(p, i)
        if oid is None:
            return None, None
        R.fetch_blobs([oid])
        for c in constraints_of(oid):
            if c.key == key:
                return True, R.state(chain[i]["h"], prefetch=(c.kind != "path")).check(c)
        return False, None

    events = []
    for p in files:
        vset = set(versions[p])
        for key, e in timeline[p].items():
            obs = sorted(e["obs"].items())
            for (a, ca), (b, cb) in zip(obs, obs[1:]):
                if ca > 0 and cb == 0:
                    # break between a and b with the constraint present at both ends; bisect for first bad index
                    lo, hi = a, b
                    exact = True
                    while hi - lo > 1:
                        mid = (lo + hi) // 2
                        pres, ok = present_and_ok(p, key, mid)
                        if pres is None or pres is False:
                            exact = False
                            lo = mid
                            continue
                        if ok:
                            lo = mid
                        else:
                            hi = mid
                    events.append({"file": p, "key": key, "type": "break", "idx": hi, "prev": lo, "exact": exact,
                                   "ts": chain[hi]["ts"], "commit": chain[hi]["h"], "ctx_touched": hi in vset})
            # sync update: constraint disappears at version commit v while its target is invalidated by v itself
            snapset = e["obs"]
            for v in versions[p]:
                if v - 1 in snapset and v not in snapset and snapset[v - 1] > 0 and v in file_oid[p]:
                    c = K.Constraint(e["kind"], e["target"], 0, "", e["sub"])
                    ok_now = R.state(chain[v]["h"], prefetch=(c.kind != "path")).check(c)
                    events.append({"file": p, "key": key, "type": "sync_removal" if not ok_now else "removal_valid",
                                   "idx": v, "ts": chain[v]["ts"], "commit": chain[v]["h"]})
                elif v - 1 in snapset and v not in snapset and snapset[v - 1] == 0 and v in file_oid[p]:
                    events.append({"file": p, "key": key, "type": "removal_broken", "idx": v, "ts": chain[v]["ts"],
                                   "commit": chain[v]["h"]})
    out = {
        "repo": full, "meta": meta, "head": head, "n_chain": len(chain), "t0": t0, "symlinks": symlinks,
        "snaps": [[s, chain[s]["ts"], chain[s]["h"]] for s in snaps], "fully_enumerated": n <= MAX_EVEN,
        "files": {p: {"versions": [[v, chain[v]["ts"]] for v in versions[p]],
                      "head_text": R.blob_cache.get(file_oid[p].get(snaps[-1], ""), "") if p != BASELINE else "",
                      "version_oids": [[v, file_oid[p].get(v)] for v in versions[p] if v in file_oid[p]],
                      "texts": {o: R.blob_cache.get(o, "") for o in set(file_oid[p].values())} if p != BASELINE else {},
                      "head_bytes": len(R.blob_cache.get(file_oid[p].get(snaps[-1], ""), "")),
                      "constraints": {k: dict(e, obs=sorted(e["obs"].items())) for k, e in timeline[p].items()}}
                  for p in files},
        "events": events,
        "commits": [[c["ts"], int(c["merge"]), c["s"], int(bool(AGENT_RX.search(c["an"] + " " + c["co"])))] for c in chain[-20000:]],
        "commits_offset": max(0, len(chain) - 20000),
        "elapsed": round(time.time() - t_start, 1),
    }
    return out


def work(full, meta, force):
    outp = os.path.join(MINED, full.replace("/", "__") + ".json.gz")
    if os.path.exists(outp) and not force:
        return full, "cached"
    try:
        res = mine(full, meta)
    except Exception as ex:
        res = {"repo": full, "skip": "error: " + str(ex)[:300], "trace": traceback.format_exc()[-800:]}
    with gzip.open(outp, "wt") as f:
        json.dump(res, f)
    return full, res.get("skip", f"ok {res.get('elapsed')}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    sample = json.load(open(os.path.join(CACHE, "search", "sample.json")))["repos"]
    repos = [a.only] if a.only else sorted(sample)
    if a.limit:
        repos = repos[:a.limit]
    os.makedirs(CLONES, exist_ok=True)
    os.makedirs(MINED, exist_ok=True)
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(work, r, sample.get(r, {}), a.force) for r in repos]
        for i, f in enumerate(as_completed(futs)):
            print(i + 1, len(repos), *f.result(), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stage 10: build the human labelling kit (artifact/labelling/). Run once, with the clones present:  python3 src/s10_labelling_kit.py

It is NOT part of the default run. It refuses to run without the clones (the evidence columns would be empty)
and refuses to touch a kit in which any label cell is filled, unless --force is given.

Sheets (one blinded copy per rater, independent random orders, random item identifiers, empty label columns):
  A_extraction  head constraints of context files, five strata by checker status
  B_breaks      break episodes, context files and README, with instruction context, commit link and commit record
  S_insync      in-sync update events, context files and README
  L_lenient     anchored path constraints satisfied at the head only by base name or suffix, with the matched locations
  R_recall      a uniform random sample of ALL non-blank lines of 30 context files, with what the tool extracted from each line
calibration/    20 items outside the samples, labelled jointly by the raters before they start
key/            strata, artefact, population sizes and sampling weights (raters must not open it)

Items in the development samples that the AI assistant labelled (results/validation_sample.csv) are excluded from A and B.
No label is written by this script.
"""
import csv, gzip, json, os, random, re, subprocess, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compiler as K

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ART, "results")
KIT = os.path.join(ART, "labelling")
CACHE = os.environ.get("S03_CACHE") or os.path.expanduser("~/.cache/context-rot-study/S03")
SEED = 20261005
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1")
LABEL_COLS = {"A_extraction": ["is_repo_reference", "notes"], "B_breaks": ["true_staleness", "reason"],
              "S_insync": ["target_invalidated", "reference_updated", "notes"], "L_lenient": ["matched_is_intended", "notes"],
              "R_recall": ["true_path", "true_script", "true_target", "true_manifest", "true_dep", "tool_wrong", "notes"]}


def rows(name):
    return list(csv.DictReader(open(os.path.join(RES, name))))


_mined = collections.OrderedDict()


def mined(repo):
    if repo not in _mined:
        src = os.path.join(CACHE, "mined", repo.replace("/", "__") + ".json.gz")
        if not os.path.exists(src):
            src = os.path.join(ART, "data", "mined", repo.replace("/", "__") + ".json.gz")
        with gzip.open(src, "rt") as f:
            _mined[repo] = json.load(f)
        if len(_mined) > 40:
            _mined.popitem(last=False)
    return _mined[repo]


def git(repo, *args):
    d = os.path.join(CACHE, "clones", repo.replace("/", "__"))
    try:
        return subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, timeout=120, env=ENV).stdout
    except Exception:
        return ""


def context(text, raw, line, width=2):
    lines = text.splitlines()
    if not lines:
        return raw
    idx = next((i for i, l in enumerate(lines) if raw[:60] and raw[:60] in l), max(0, int(line) - 1))
    lo, hi = max(0, idx - width), min(len(lines), idx + width + 1)
    return " ⏎ ".join(l.strip()[:220] for l in lines[lo:hi])


def url_file(repo, commit, path, line=None):
    return f"https://github.com/{repo}/blob/{commit}/{path}" + (f"#L{line}" if line else "")


def write(path, rows_, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_)


def emit(name, items, shown, key_cols, rng):
    """Assign random identifiers (no relation to stratum), write the key and one independently shuffled sheet per rater."""
    prefix = name.split("_")[0]
    order = list(range(len(items)))
    rng.shuffle(order)
    for n, i in enumerate(order):
        items[i]["id"] = f"{prefix}{n + 1:03d}"
    write(os.path.join(KIT, "key", name + ".csv"), sorted(items, key=lambda x: x["id"]), ["id"] + key_cols)
    for r, rater in enumerate(("rater1", "rater2")):
        o = items[:]
        random.Random(SEED + 101 * (r + 1) + len(name)).shuffle(o)
        write(os.path.join(KIT, rater, name + ".csv"), [dict({k: it.get(k, "") for k in ["id"] + shown}, **{c: "" for c in LABEL_COLS[name]}) for it in o],
              ["id"] + shown + LABEL_COLS[name])


def commit_record(repo, commit, target, kind):
    out = git(repo, "show", "--no-renames", "--diff-merges=first-parent", "--name-status", "--format=SUBJ %s", commit)
    ls = out.splitlines()
    subj = next((l[5:] for l in ls if l.startswith("SUBJ ")), "")
    ch = [l.replace("\t", " ") for l in ls if "\t" in l]
    t = target.rstrip("/")
    base = t.rsplit("/", 1)[-1].replace("*", "")
    man = [l for l in ch if l.rsplit("/", 1)[-1] in ("package.json", "Makefile", "makefile", "justfile", "Justfile", "pyproject.toml") or l.endswith(".mk")]
    hits = [l for l in ch if t in l or (base and base in l)]
    return subj[:120], len(ch), " ; ".join((hits if kind == "path" else man + hits)[:15]) or " ; ".join(ch[:15])


def filled():
    for rater in ("rater1", "rater2"):
        for name, cols in LABEL_COLS.items():
            p = os.path.join(KIT, rater, name + ".csv")
            if os.path.exists(p) and any((r.get(c) or "").strip() for r in csv.DictReader(open(p)) for c in cols):
                return p
    return None


def main():
    if not os.path.isdir(os.path.join(CACHE, "clones")):
        sys.exit("refusing to build the kit: clones not found under " + CACHE + " (commit records and matched files would be empty)")
    f_ = filled()
    if f_ and "--force" not in sys.argv:
        sys.exit("refusing to rebuild the kit: labels found in " + f_)
    rng = random.Random(SEED)
    cons_all = rows("constraints.csv")
    cons = [c for c in cons_all if c["is_ctx"] == "1"]
    ckey = {(c["repo"], c["file"], c["key"]): c for c in cons_all}
    brk = [b for b in rows("breaks.csv") if b["born_valid"] == "1"]
    rem = [r for r in rows("removals.csv") if r["type"] == "sync_removal" and r["born_valid"] == "1"]
    files = [f for f in rows("files.csv") if f["is_ctx"] == "1"]
    dev = {(r["repo"], r["file"], r["kind"], r["target"]) for r in rows("validation_sample.csv")}
    isdev = lambda x: (x["repo"], x["file"], x["kind"], x["target"]) in dev
    summary, calib = {"seed": SEED}, []

    # ---------------------------------------------------------------- A
    live = [c for c in cons if c["live_head"] == "1" and not isdev(c)]
    strata = {"anchored_violated": ([c for c in live if c["born_valid"] == "1" and c["head_code"] == "0"], 60),
              "anchored_satisfied_exact": ([c for c in live if c["born_valid"] == "1" and c["head_code"] == "1"], 40),
              "anchored_satisfied_lenient": ([c for c in live if c["born_valid"] == "1" and c["head_code"] == "2"], 30),
              "never_valid": ([c for c in live if c["ever_valid"] == "0"], 40),
              "entered_invalid_later_valid": ([c for c in live if c["born_valid"] == "0" and c["ever_valid"] == "1"], 20)}
    A = []
    for sname, (pool, n) in strata.items():
        pick = rng.sample(pool, min(n + 2, len(pool)))
        for j, c in enumerate(pick):
            m = mined(c["repo"])
            it = {"repo": c["repo"], "file": c["file"], "kind": c["kind"], "extracted": c["target"],
                  "context": context(m["files"][c["file"]]["head_text"], c["raw"], c["line"]),
                  "link": url_file(c["repo"], m["head"], c["file"], c["line"]), "stratum": sname, "stratum_population": len(pool)}
            (A if j < n else calib).append(dict(it, sheet="A_extraction") if j >= n else it)
        summary["A_" + sname] = {"population": len(pool), "sampled": min(n, len(pool))}
    emit("A_extraction", A, ["repo", "file", "kind", "extracted", "context", "link"], ["stratum", "stratum_population"], rng)

    # ---------------------------------------------------------------- B and S
    def event_item(e, typ):
        m = mined(e["repo"])
        c = ckey[(e["repo"], e["file"], e["key"])]
        fd = m["files"][e["file"]]
        text = ""
        if e["file"] != "README.md":
            oid = None
            idx = next((x["idx"] for x in m["events"] if x["file"] == e["file"] and x["key"] == e["key"] and x["commit"] == e["commit"]), None)
            for v, o in fd.get("version_oids", []):
                if idx is None or v < idx or (typ == "break" and v <= idx):
                    oid = o
            text = fd["texts"].get(oid, "") if oid else ""
        subj, n, rec = commit_record(e["repo"], e["commit"], c["target"], c["kind"]) if e["commit"] else ("", "", "")
        return {"repo": e["repo"], "file": e["file"], "kind": c["kind"], "reference": c["target"],
                "instruction_context": context(text, c["raw"], 1), "commit": f"https://github.com/{e['repo']}/commit/{e['commit']}" if e["commit"] else "",
                "commit_subject": subj, "files_changed": n, "commit_record": rec, "artefact": "context" if e["is_ctx"] == "1" else "readme"}

    Bs = []
    for art, is_ctx in (("context", "1"), ("readme", "0")):
        pool = [b for b in brk if b["is_ctx"] == is_ctx and b["commit"] and not (is_ctx == "1" and isdev(b))]
        for st, sel, n in (("non_path", lambda b: b["kind"] != "path", 30), ("path", lambda b: b["kind"] == "path", 60 if art == "context" else 52)):
            sp = [b for b in pool if sel(b)]
            pick = rng.sample(sp, min(n + 2, len(sp))) if len(sp) > n else sp
            for j, b in enumerate(pick):
                it = dict(event_item(b, "break"), stratum=f"{art}_{st}", stratum_population=len(sp))
                (Bs if j < n else calib).append(it if j < n else dict(it, sheet="B_breaks"))
            summary[f"B_{art}_{st}"] = {"population": len(sp), "sampled": min(n, len(sp))}
    emit("B_breaks", Bs, ["repo", "file", "kind", "reference", "instruction_context", "commit", "commit_subject", "files_changed", "commit_record"],
         ["artefact", "stratum", "stratum_population"], rng)
    Ss = []
    for art, is_ctx in (("context", "1"), ("readme", "0")):
        pool = [r for r in rem if r["is_ctx"] == is_ctx and r["commit"]]
        pick = rng.sample(pool, 63)
        for j, r in enumerate(pick):
            it = dict(event_item(r, "sync"), stratum=art, stratum_population=len(pool))
            (Ss if j < 60 else calib).append(it if j < 60 else dict(it, sheet="S_insync"))
        summary[f"S_{art}"] = {"population": len(pool), "sampled": 60}
    emit("S_insync", Ss, ["repo", "file", "kind", "reference", "instruction_context", "commit", "commit_subject", "files_changed", "commit_record"],
         ["artefact", "stratum", "stratum_population"], rng)

    # ---------------------------------------------------------------- L
    lpool = [c for c in cons if c["live_head"] == "1" and c["born_valid"] == "1" and c["kind"] == "path" and c["head_code"] == "2" and "*" not in c["target"]]
    Ls, trees = [], {}
    cand = rng.sample(lpool, 140)
    for c in cand:
        if len(Ls) >= 100:
            break
        if c["repo"] not in trees:
            fs = git(c["repo"], "ls-tree", "-r", "--name-only", "HEAD").splitlines()
            ds = set()
            for p in fs:
                parts = p.split("/")
                for k in range(1, len(parts)):
                    ds.add("/".join(parts[:k]))
            trees[c["repo"]] = (fs, sorted(ds))
        fs, ds = trees[c["repo"]]
        t = c["target"].rstrip("/")
        pool = ds if c["target"].endswith("/") else fs + ds
        match = sorted({p for p in pool if p == t or p.endswith("/" + t)})
        if not match:
            continue
        m = mined(c["repo"])
        Ls.append({"repo": c["repo"], "file": c["file"], "reference": c["target"], "context": context(m["files"][c["file"]]["head_text"], c["raw"], c["line"]),
                   "matched_locations": len(match), "matched_examples": " ; ".join(match[:5]), "link": url_file(c["repo"], m["head"], c["file"], c["line"]),
                   "is_bare": c["is_bare"]})
    emit("L_lenient", Ls, ["repo", "file", "reference", "context", "matched_locations", "matched_examples", "link"], ["is_bare", "matched_locations"], rng)
    summary["L"] = {"population": len(lpool), "sampled": len(Ls), "sample_with_more_than_one_match": sum(1 for l in Ls if l["matched_locations"] > 1)}

    # ---------------------------------------------------------------- R: uniform sample of all non-blank lines
    rfiles = rng.sample([f for f in files if int(f["bytes"]) >= 500], 30)
    Rs, PER = [], 20
    for f in rfiles:
        m = mined(f["repo"])
        text = m["files"][f["file"]]["head_text"]
        cs = collections.defaultdict(list)
        for c in K.compile_text(text):
            cs[c.line].append(c)
        lines = [(i, l) for i, l in enumerate(text.splitlines(), 1) if l.strip()]
        take = sorted(rng.sample(lines, min(PER, len(lines))))
        for i, l in take:
            ex = cs.get(i, [])
            cnt = collections.Counter(c.kind for c in ex)
            Rs.append({"repo": f["repo"], "file": f["file"], "line": i, "text": l.strip()[:400], "link": url_file(f["repo"], m["head"], f["file"], i),
                       "tool_extracted": " ; ".join(f"{c.kind}: {c.target}" for c in ex) or "(nothing)",
                       "file_lines": len(lines), "file_sampled": len(take), **{"tool_" + k: cnt.get(k, 0) for k in ("path", "script", "target", "manifest", "dep")}})
    emit("R_recall", Rs, ["repo", "file", "line", "text", "tool_extracted", "link"],
         ["repo", "file", "file_lines", "file_sampled", "tool_path", "tool_script", "tool_target", "tool_manifest", "tool_dep"], rng)
    summary["R"] = {"files": len(rfiles), "lines": len(Rs), "lines_with_extraction": sum(1 for r in Rs if r["tool_extracted"] != "(nothing)"),
                    "frame": "all non-blank lines of the head version, 30 files drawn uniformly from context files of at least 500 bytes, up to 20 lines per file drawn uniformly, weighted by lines over sampled lines"}

    # ---------------------------------------------------------------- calibration round (outside the samples)
    rng.shuffle(calib)
    calib = calib[:20]
    for i, it in enumerate(calib):
        it["id"] = f"C{i + 1:02d}"
    write(os.path.join(KIT, "calibration", "calibration_items.csv"), calib,
          ["id", "sheet", "repo", "file", "kind", "extracted", "reference", "context", "instruction_context", "commit", "commit_record", "link", "label_agreed", "notes"])
    summary["calibration_items"] = len(calib)
    summary["judgements_per_rater"] = len(A) + len(Bs) + 2 * len(Ss) + len(Ls) + len(Rs)
    json.dump(summary, open(os.path.join(KIT, "kit_summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stage 2: fetch repository metadata for the search hits and draw the study sample.

Inclusion: not a fork, not archived, at least MIN_STARS stars, disk usage at most MAX_KB,
context file at the repository root (or .github/ or .claude/ for the two tools that read it there).
Eligible repositories are shuffled within file type before a cap of 10,000 per type.
The pilot is below that cap and includes every eligible repository.
"""
import json, os, random, subprocess, sys, time, collections

CACHE = os.path.expanduser(os.environ.get("S03_CACHE", "~/.cache/context-rot-study/S03"))
HITS = os.path.join(CACHE, "search", "hits.jsonl")
META = os.path.join(CACHE, "search", "meta.json")
OUT = os.path.join(CACHE, "search", "sample.json")
MIN_STARS, MAX_KB, PER_TYPE, SEED = 50, 150_000, 10_000, 20261003
ROOT_OK = {"AGENTS.md": {"AGENTS.md"}, "CLAUDE.md": {"CLAUDE.md", ".claude/CLAUDE.md"},
           ".cursorrules": {".cursorrules"}, "copilot-instructions.md": {".github/copilot-instructions.md"}}


def gql(repos):
    parts = []
    for i, r in enumerate(repos):
        o, n = r.split("/", 1)
        parts.append(f'r{i}: repository(owner: "{o}", name: "{n}") {{ nameWithOwner stargazerCount isFork isArchived '
                     f'diskUsage pushedAt createdAt primaryLanguage {{ name }} defaultBranchRef {{ name }} }}')
    q = "query {" + "\n".join(parts) + "}"
    for attempt in range(4):
        p = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True, timeout=120)
        try:
            d = json.loads(p.stdout).get("data") or {}
            return {repos[i]: d.get(f"r{i}") for i in range(len(repos))}
        except Exception:
            time.sleep(10)
    return {}


def main():
    cand = collections.defaultdict(set)  # repo -> set of file types found at root
    nhits = 0
    for line in open(HITS):
        d = json.loads(line)
        for it in d["items"]:
            nhits += 1
            if it["path"] in ROOT_OK[d["filename"]]:
                cand[it["repo"]].add(d["filename"])
    repos = sorted(cand)
    meta = json.load(open(META)) if os.path.exists(META) else {}
    todo = [r for r in repos if r not in meta]
    for i in range(0, len(todo), 40):
        meta.update(gql(todo[i:i + 40]))
        json.dump(meta, open(META, "w"))
        print("meta", i, len(todo), flush=True)
    elig = {}
    for r in repos:
        m = meta.get(r)
        if not m or m["isFork"] or m["isArchived"]:
            continue
        if m["stargazerCount"] < MIN_STARS or (m["diskUsage"] or 0) > MAX_KB:
            continue
        elig[r] = m
    rng = random.Random(SEED)
    sample = {}
    for ft in ROOT_OK:
        pool = sorted(r for r in elig if ft in cand[r])
        rng.shuffle(pool)
        for r in pool[:PER_TYPE]:
            sample[r] = elig[r]
    funnel = {"search_hits": nhits, "repos_with_root_file": len(repos), "metadata_found": sum(1 for r in repos if meta.get(r)),
              "eligible": len(elig), "sampled": len(sample), "min_stars": MIN_STARS, "max_kb": MAX_KB, "per_type": PER_TYPE,
              "seed": SEED, "eligible_by_type": {ft: sum(1 for r in elig if ft in cand[r]) for ft in ROOT_OK}}
    json.dump({"funnel": funnel, "repos": sample}, open(OUT, "w"), indent=1)
    print(json.dumps(funnel, indent=1))


if __name__ == "__main__":
    main()

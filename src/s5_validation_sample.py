#!/usr/bin/env python3
"""Stage 5: draw the seeded random samples that were inspected by hand.

A  extraction sample: constraints of context files at HEAD (is the token a real repository reference
   that the checker interprets as intended)
B  break sample: break episodes of born-valid constraints in context files, with git evidence
C  never-valid sample: constraints at HEAD that were never satisfied (what are they)
Writes results/validation_sample.csv. Labels live in results/validation_labels.csv (hand written).
"""
import csv, os, random, subprocess, sys

CACHE = os.environ.get("S03_CACHE") or os.path.expanduser("~/.cache/context-rot-study/S03")
if not os.path.isdir(os.path.join(CACHE, "mined")):  # fall back to the copy shipped inside the package
    CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
SEED, NA, NB, NC = 20261003, 100, 60, 60


def evidence(repo, commit, target):
    d = os.path.join(CACHE, "clones", repo.replace("/", "__"))
    if not commit or not os.path.isdir(d):
        return ""
    p = subprocess.run(["git", "-C", d, "show", "--no-renames", "--diff-merges=first-parent", "--name-status", "--format=SUBJ %s", commit],
                       capture_output=True, text=True, timeout=120)
    lines = p.stdout.splitlines()
    subj = next((l[5:] for l in lines if l.startswith("SUBJ ")), "")
    t = target.rstrip("/")
    base = t.rsplit("/", 1)[-1].replace("*", "")
    hits = [l.replace("\t", " ") for l in lines if l[:1] in "ADMRT" and "\t" in l and (t in l or (base and base in l))]
    n = sum(1 for l in lines if "\t" in l)
    return f"[{subj[:70]}] files={n} " + " ; ".join(hits[:4])


def main():
    rng = random.Random(SEED)
    cons = list(csv.DictReader(open(os.path.join(RES, "constraints.csv"))))
    brk = list(csv.DictReader(open(os.path.join(RES, "breaks.csv"))))
    A = [c for c in cons if c["is_ctx"] == "1" and c["live_head"] == "1"]
    Bp = [b for b in brk if b["is_ctx"] == "1" and b["born_valid"] == "1"]
    C = [c for c in A if c["ever_valid"] == "0"]
    rows = []
    for i, c in enumerate(rng.sample(A, min(NA, len(A)))):
        rows.append({"id": f"A{i:03d}", "set": "A", "repo": c["repo"], "file": c["file"], "kind": c["kind"], "target": c["target"],
                     "status": "ok" if c["head_code"] != "0" else "violated", "born_valid": c["born_valid"], "evidence": "", "raw": c["raw"]})
    for i, b in enumerate(rng.sample(Bp, min(NB, len(Bp)))):
        rows.append({"id": f"B{i:03d}", "set": "B", "repo": b["repo"], "file": b["file"], "kind": b["kind"], "target": b["target"],
                     "status": b["end"], "born_valid": b["born_valid"], "evidence": evidence(b["repo"], b["commit"], b["target"]), "raw": b["raw"]})
    for i, c in enumerate(rng.sample(C, min(NC, len(C)))):
        rows.append({"id": f"C{i:03d}", "set": "C", "repo": c["repo"], "file": c["file"], "kind": c["kind"], "target": c["target"],
                     "status": "never valid", "born_valid": "0", "evidence": "", "raw": c["raw"]})
    with open(os.path.join(RES, "validation_sample.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows; populations A", len(A), "B", len(Bp), "C", len(C))


if __name__ == "__main__":
    main()

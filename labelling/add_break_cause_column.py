#!/usr/bin/env python3
"""Add an empty break_cause column to labelling/rater1/B_breaks.csv and labelling/rater2/B_breaks.csv (idempotent). Never edits existing labels."""
import csv, os, sys
ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.environ.get("S03_KIT") or os.path.join(ART, "labelling")
for rater in ("rater1", "rater2"):
    p = os.path.join(KIT, rater, "B_breaks.csv")
    rows = list(csv.DictReader(open(p, newline="")))
    cols = list(rows[0].keys())
    if "break_cause" in cols:
        print(rater, "already has break_cause"); continue
    filled = sum(1 for r in rows if (r.get("true_staleness") or "").strip())
    if filled:
        print(f"WARNING {rater}: {filled} true_staleness cells already filled; the new column starts empty, fill it for every 'yes' item.", file=sys.stderr)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["break_cause"]); w.writeheader()
        for r in rows: w.writerow({**r, "break_cause": ""})
    print(rater, "break_cause added to", len(rows), "rows")
 
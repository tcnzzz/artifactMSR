#!/usr/bin/env python3
"""Stage 7: summarise the hand labels (validation_labels.csv, conflict_labels.csv) into validation_summary.json."""
import csv, json, os, collections, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s4_analyze import wilson

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def main():
    sample = {r["id"]: r for r in csv.DictReader(open(os.path.join(RES, "validation_sample.csv")))}
    labels = list(csv.DictReader(open(os.path.join(RES, "validation_labels.csv"))))
    missing = [i for i in sample if i not in {l["id"] for l in labels}]
    assert not missing, f"unlabelled sample rows: {missing[:5]}"
    by = collections.defaultdict(collections.Counter)
    for l in labels:
        assert l["id"] in sample, l["id"]
        by[l["set"]][l["label"]] += 1
    out = {}
    a, b = by["A"], by["B"]
    na, nb = sum(a.values()), sum(b.values())
    out["extraction"] = {"n": na, "genuine": a["genuine reference"], "precision": a["genuine reference"] / na, "wilson": wilson(a["genuine reference"], na)}
    out["breaks"] = {"n": nb, "true_staleness": b["true staleness"], "precision": b["true staleness"] / nb, "wilson": wilson(b["true staleness"], nb)}
    nc = sum(by["C"].values())
    out["never_valid"] = {"n": nc, "categories": {k: {"count": v, "share": v / nc, "wilson": wilson(v, nc)} for k, v in by["C"].most_common()}}
    # violated rows inside the extraction sample, split by anchoring
    va = [l for l in labels if l["set"] == "A" and sample[l["id"]]["status"] == "violated"]
    out["extraction"]["violated_in_sample"] = len(va)
    out["extraction"]["violated_not_anchored"] = sum(1 for l in va if sample[l["id"]]["born_valid"] == "0")
    conf = list(csv.DictReader(open(os.path.join(RES, "conflict_labels.csv"))))
    cc = collections.Counter(c["label"] for c in conf)
    out["conflicts"] = {"groups": len(conf), "files": len({(c["repo"], c["file"]) for c in conf}), "labels": dict(cc),
                        "true_contradictions": cc["true contradiction"], "precision_upper_wilson": wilson(cc["true contradiction"], len(conf))[1]}
    json.dump(out, open(os.path.join(RES, "validation_summary.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

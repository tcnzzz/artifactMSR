#!/usr/bin/env python3
"""Stage 4b: reanalyses requested in review round 1, computed from the row-level CSV files of stage 4.

Writes results/robustness.json.
  invalidation  invalidations (in-sync updates plus breaks) per 100 constraint-years, both artefacts
  cif           cumulative incidence with competing risks (break, in-sync removal, removal while valid)
  insync, open  the two maintenance contrasts under alternative units, trimming and leave-one-repository-out
  drift_sens    head drift and break rate without constraints that can hardly be falsified
  lenient       mechanical estimate of breaks hidden by lenient path matching
  enumerated    key figures on fully enumerated repositories only
  age           drift by age, truncated, and the within-cohort curve
  denominators  share of files with a violation over both denominators
"""
import csv, json, os, sys, collections, math
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s4_analyze import wilson

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
B, SEED = 2000, 20261003
rng = np.random.default_rng(SEED)


def rows(name):
    return list(csv.DictReader(open(os.path.join(RES, name))))


def f(x):
    return float(x) if x != "" else float("nan")


cons = rows("constraints.csv")
brk = rows("breaks.csv")
rem = rows("removals.csv")
files = rows("files.csv")
repos = {r["repo"]: r for r in rows("repos.csv")}
ALL_REPOS = sorted(repos)
for c in cons:
    c["exposure_days"] = float(c["exposure_days"]); c["n_breaks"] = int(c["n_breaks"])
    c["days"] = float(c["days_to_break_or_censor"])
A = lambda c: c["born_valid"] == "1"
anch = {"1": [c for c in cons if c["is_ctx"] == "1" and A(c)], "0": [c for c in cons if c["is_ctx"] == "0" and A(c)]}
breaks = {k: [b for b in brk if b["is_ctx"] == k and b["born_valid"] == "1"] for k in "10"}
syncs = {k: [r for r in rem if r["is_ctx"] == k and r["type"] == "sync_removal" and r["born_valid"] == "1"] for k in "10"}
LAB = {"1": "context", "0": "readme"}


def boot_weights():
    idx = rng.integers(0, len(ALL_REPOS), len(ALL_REPOS))
    return collections.Counter(ALL_REPOS[i] for i in idx)


def paired(fn, b=B):
    """fn(weight function) -> dict of floats. Returns estimate and percentile intervals (cluster bootstrap over repositories)."""
    est = fn(lambda r: 1)
    acc = collections.defaultdict(list)
    for _ in range(b):
        w = boot_weights()
        for k, v in fn(lambda r: w.get(r, 0)).items():
            acc[k].append(v)
    return {k: {"est": est[k], "ci": np.nanpercentile(np.array(acc[k], float), [2.5, 97.5]).tolist()} for k in est}


OUT = {}

# ------------------------------------------------------------------ 1. invalidation versus break rates
def rates(w, subset=None):
    out = {}
    for k in "10":
        cs = anch[k] if subset is None else [c for c in anch[k] if subset(c)]
        keys = {(c["repo"], c["file"], c["key"]) for c in cs} if subset is not None else None
        ex = sum(w(c["repo"]) * c["exposure_days"] for c in cs) / 365.25
        nb = sum(w(c["repo"]) * c["n_breaks"] for c in cs)
        ns = sum(w(r["repo"]) for r in syncs[k] if keys is None or (r["repo"], r["file"], r["key"]) in keys)
        out[LAB[k] + "_break_rate"] = 100 * nb / ex if ex else float("nan")
        out[LAB[k] + "_insync_rate"] = 100 * ns / ex if ex else float("nan")
        out[LAB[k] + "_invalidation_rate"] = 100 * (nb + ns) / ex if ex else float("nan")
    out["invalidation_ratio_ctx_over_readme"] = out["context_invalidation_rate"] / out["readme_invalidation_rate"]
    out["break_ratio_ctx_over_readme"] = out["context_break_rate"] / out["readme_break_rate"]
    return out


OUT["invalidation"] = paired(rates)
OUT["invalidation"]["counts"] = {LAB[k]: {"breaks": sum(c["n_breaks"] for c in anch[k]), "in_sync": len(syncs[k]),
                                          "exposure_years": sum(c["exposure_days"] for c in anch[k]) / 365.25} for k in "10"}
# README restricted to references whose entry is observed (not left-truncated), and path constraints only
OUT["invalidation_entry_observed"] = paired(lambda w: rates(w, lambda c: c["left_truncated"] == "0"), b=1000)
OUT["invalidation_paths_only"] = paired(lambda w: rates(w, lambda c: c["kind"] == "path"), b=1000)
OUT["invalidation"]["share_readme_left_truncated"] = float(np.mean([c["left_truncated"] == "1" for c in anch["0"]]))
half = lambda rate: math.log(2) / (rate / 100.0)
OUT["invalidation"]["implied_half_life_years"] = {"context": half(OUT["invalidation"]["context_invalidation_rate"]["est"]),
                                                  "readme": half(OUT["invalidation"]["readme_invalidation_rate"]["est"])}

# ------------------------------------------------------------------ 2. cumulative incidence with competing risks
CAUSES = ["break", "sync_removal", "removal_valid"]


def cif(cs, w, marks=(90, 180, 365)):
    """Aalen-Johansen estimator. cs: constraint rows. Returns {cause: [CIF at marks]} and overall survival."""
    data = sorted(((c["days"], c["terminal"], w(c["repo"])) for c in cs if w(c["repo"]) > 0), key=lambda x: x[0])
    n = sum(x[2] for x in data)
    surv, cum = 1.0, {k: 0.0 for k in CAUSES}
    res = {k: [] for k in CAUSES}
    res["event_free"] = []
    mi, i = 0, 0
    marks = list(marks)
    while i < len(data) and mi < len(marks):
        t = data[i][0]
        while mi < len(marks) and marks[mi] < t:
            for k in CAUSES:
                res[k].append(cum[k])
            res["event_free"].append(surv)
            mi += 1
        j, d, tot = i, collections.Counter(), 0
        while j < len(data) and data[j][0] == t:
            tot += data[j][2]
            if data[j][1] in cum:
                d[data[j][1]] += data[j][2]
            j += 1
        if n > 0:
            for k in CAUSES:
                cum[k] += surv * d[k] / n
            surv *= 1 - sum(d.values()) / n
        n -= tot
        i = j
    while mi < len(marks):
        for k in CAUSES:
            res[k].append(cum[k])
        res["event_free"].append(surv)
        mi += 1
    return res


def cif_stats(w):
    out = {}
    for k, cs in (("context", anch["1"]), ("readme_entry_observed", [c for c in anch["0"] if c["left_truncated"] == "0"])):
        r = cif(cs, w)
        for cause in CAUSES + ["event_free"]:
            for m, v in zip((90, 180, 365), r[cause]):
                out[f"{k}_{cause}_{m}"] = v
        for m in (90, 180, 365):
            out[f"{k}_invalidated_{m}"] = out[f"{k}_break_{m}"] + out[f"{k}_sync_removal_{m}"]
    return out


OUT["cif"] = paired(cif_stats, b=500)
OUT["cif"]["n"] = {"context": len(anch["1"]), "readme_entry_observed": sum(1 for c in anch["0"] if c["left_truncated"] == "0")}
grid = list(range(0, 541, 10))
OUT["cif_curves"] = {"grid": grid}
for k, cs in (("context", anch["1"]), ("readme_entry_observed", [c for c in anch["0"] if c["left_truncated"] == "0"])):
    OUT["cif_curves"][k] = cif(cs, lambda r: 1, marks=grid)

# ------------------------------------------------------------------ 3. robustness of the in-sync and open contrasts
def insync_share(k, w, quick=None):
    """quick: None, 'day' (break repaired within one day counts as in sync) or 'commits' (within three commits)."""
    sy = sum(w(r["repo"]) for r in syncs[k])
    br = 0
    for b in breaks[k]:
        fast = False
        if quick == "day":
            fast = b["end"] != "open" and float(b["days_broken"]) <= 1.0
        elif quick == "commits":
            fast = b["end"] != "open" and b["commits_broken"] != "" and int(b["commits_broken"]) <= 3
        if fast:
            sy += w(b["repo"])
        else:
            br += w(b["repo"])
    return sy / (sy + br) if sy + br else float("nan")


def open_share(k, w, min_age=None):
    bs = [b for b in breaks[k] if min_age is None or float(b["days_before_head"]) >= min_age]
    den = sum(w(b["repo"]) for b in bs)
    return sum(w(b["repo"]) for b in bs if b["end"] == "open") / den if den else float("nan")


def contrast(fn):
    def g(w):
        c, r = fn("1", w), fn("0", w)
        return {"context": c, "readme": r, "diff": c - r}
    return g


R = {}
R["event_level"] = paired(contrast(insync_share))
R["quick_repair_one_day_as_in_sync"] = paired(contrast(lambda k, w: insync_share(k, w, "day")))
R["quick_repair_three_commits_as_in_sync"] = paired(contrast(lambda k, w: insync_share(k, w, "commits")))
R["quick_counts"] = {LAB[k]: {"closed": sum(1 for b in breaks[k] if b["end"] != "open"),
                              "closed_within_one_day": sum(1 for b in breaks[k] if b["end"] != "open" and float(b["days_broken"]) <= 1.0),
                              "closed_within_three_commits": sum(1 for b in breaks[k] if b["end"] != "open" and b["commits_broken"] != "" and int(b["commits_broken"]) <= 3)} for k in "10"}


# commit level: an invalidating commit is in sync when no anchored instruction is left broken by it
def commit_level(w):
    out = {}
    for k in "10":
        com = collections.defaultdict(lambda: [0, 0])
        for r in syncs[k]:
            com[(r["repo"], r["commit"])][0] += 1
        for b in breaks[k]:
            com[(b["repo"], b["commit"] or ("?" + b["key"]))][1] += 1
        den = sum(w(c[0]) for c in com)
        out[LAB[k]] = sum(w(c[0]) for c, v in com.items() if v[1] == 0) / den if den else float("nan")
        out[LAB[k] + "_commits"] = len(com)
    out["diff"] = out["context"] - out["readme"]
    return out


R["commit_level"] = paired(commit_level)


def per_repo(k, kind):
    d = collections.defaultdict(lambda: [0, 0])
    if kind == "insync":
        for r in syncs[k]:
            d[r["repo"]][0] += 1
        for b in breaks[k]:
            d[b["repo"]][1] += 1
    else:
        for b in breaks[k]:
            d[b["repo"]][0 if b["end"] == "open" else 1] += 1
    return {r: v[0] / (v[0] + v[1]) for r, v in d.items()}, {r: v[0] + v[1] for r, v in d.items()}


def repo_block(kind, fn):
    pc, nc = per_repo("1", kind)
    pr, nr = per_repo("0", kind)
    both = sorted(set(pc) & set(pr))
    dd = np.array([pc[r] - pr[r] for r in both])
    blk = {"repo_mean": {"context": float(np.mean(list(pc.values()))), "readme": float(np.mean(list(pr.values()))),
                         "context_repos": len(pc), "readme_repos": len(pr)},
           "both_sides": {"repos": len(both), "mean_diff": float(dd.mean()), "median_diff": float(np.median(dd)),
                          "wilcoxon_p": float(stats.wilcoxon(dd).pvalue) if np.any(dd != 0) else None,
                          "mean_diff_ci": np.percentile([dd[rng.integers(0, len(dd), len(dd))].mean() for _ in range(B)], [2.5, 97.5]).tolist()}}
    blk["repo_mean"]["diff"] = blk["repo_mean"]["context"] - blk["repo_mean"]["readme"]
    # leave one repository out
    full = fn("1", lambda r: 1) - fn("0", lambda r: 1)
    loo = {}
    for r in sorted(set(nc) | set(nr)):
        loo[r] = fn("1", lambda x, r=r: 0 if x == r else 1) - fn("0", lambda x, r=r: 0 if x == r else 1)
    vals = np.array(list(loo.values()))
    blk["leave_one_out"] = {"full": full, "min": float(vals.min()), "max": float(vals.max()), "repos": len(loo),
                            "max_abs_change": float(np.max(np.abs(vals - full)))}
    # trimmed: drop the n repositories with the most events on each side
    for n in (2, 5):
        drop = set(sorted(nc, key=nc.get, reverse=True)[:n]) | set(sorted(nr, key=nr.get, reverse=True)[:n])
        w0 = lambda x, drop=drop: 0 if x in drop else 1
        c, r_ = fn("1", w0), fn("0", w0)
        keep = [x for x in ALL_REPOS if x not in drop]
        bs = []
        for _ in range(B):
            w = collections.Counter(keep[i] for i in rng.integers(0, len(keep), len(keep)))
            bs.append(fn("1", lambda x: w.get(x, 0)) - fn("0", lambda x: w.get(x, 0)))
        blk[f"trimmed_top{n}_each_side"] = {"context": c, "readme": r_, "diff": c - r_, "dropped": len(drop),
                                            "ci": np.nanpercentile(bs, [2.5, 97.5]).tolist()}
    top = sorted(nr, key=nr.get, reverse=True)
    blk["concentration"] = {"readme_top2_share_of_events": sum(nr[r] for r in top[:2]) / sum(nr.values()),
                            "readme_top10_share": sum(nr[r] for r in top[:10]) / sum(nr.values()),
                            "context_top10_share": sum(sorted(nc.values(), reverse=True)[:10]) / sum(nc.values())}
    return blk


R.update({"insync_" + k: v for k, v in repo_block("insync", insync_share).items()})
OUT["insync"] = R
O = {"event_level": paired(contrast(open_share)), "breaks_older_than_30_days": paired(contrast(lambda k, w: open_share(k, w, 30)))}
O["older_counts"] = {LAB[k]: sum(1 for b in breaks[k] if float(b["days_before_head"]) >= 30) for k in "10"}
O.update(repo_block("open", open_share))
OUT["open"] = O

# repair mode of edit repairs (context files, path constraints; texts of README versions are not stored)
er = [b for b in breaks["1"] if b["end"] == "edit_repair"]
OUT["repair_mode"] = {"edit_repairs": len(er), "classified": sum(1 for b in er if b["rewritten"] != ""),
                      "rewritten_to_valid_target": sum(1 for b in er if b["rewritten"] == "1"),
                      "deleted": sum(1 for b in er if b["rewritten"] == "0"),
                      "not_classified_non_path": sum(1 for b in er if b["rewritten"] == "")}
OUT["repair_mode"]["rewritten_share"] = OUT["repair_mode"]["rewritten_to_valid_target"] / max(1, OUT["repair_mode"]["classified"])

# ------------------------------------------------------------------ 4. drift sensitivity
def drift_of(cs):
    live = [c for c in cs if c["live_head"] == "1"]
    k = sum(1 for c in live if c["head_code"] == "0")
    ex = sum(c["exposure_days"] for c in cs) / 365.25
    nb = sum(c["n_breaks"] for c in cs)
    return {"anchored_at_head": len(live), "violated": k, "drift": k / len(live) if live else None, "wilson": wilson(k, len(live)),
            "breaks": nb, "rate_per_100cy": 100 * nb / ex if ex else None}


DS = {}
for k in "10":
    cs = anch[k]
    DS[LAB[k]] = {
        "all": drift_of(cs),
        "paths": drift_of([c for c in cs if c["kind"] == "path"]),
        "slashed_paths": drift_of([c for c in cs if c["kind"] == "path" and c["is_bare"] == "0"]),
        "bare_names": drift_of([c for c in cs if c["kind"] == "path" and c["is_bare"] == "1"]),
        "directory_paths": drift_of([c for c in cs if c["kind"] == "path" and c["is_dir"] == "1"]),
        "file_paths": drift_of([c for c in cs if c["kind"] == "path" and c["is_dir"] == "0"]),
        "strictly_anchored": drift_of([c for c in cs if c["born_code"] == "1"]),
        "non_path": drift_of([c for c in cs if c["kind"] != "path"]),
    }
    hp = [c for c in cs if c["kind"] == "path" and c["live_head"] == "1"]
    DS[LAB[k]]["share_bare_among_head_paths"] = float(np.mean([c["is_bare"] == "1" for c in hp]))
    DS[LAB[k]]["share_lenient_only_at_birth"] = float(np.mean([c["born_code"] == "2" for c in cs if c["live_head"] == "1"]))
OUT["drift_sens"] = DS

# mechanical estimate of drift hidden by lenient matching: strictly anchored constraints whose exact path is gone
# at the head while a file of the same suffix or base name still exists
L = {}
for k in "10":
    st = [c for c in anch[k] if c["born_code"] == "1" and c["live_head"] == "1" and c["kind"] == "path"]
    hid = sum(1 for c in st if c["head_code"] == "2")
    vis = sum(1 for c in st if c["head_code"] == "0")
    L[LAB[k]] = {"strictly_anchored_paths_at_head": len(st), "violated_lenient": vis, "exact_path_gone_but_lenient_match": hid,
                 "hidden_share_of_strict_violations": hid / max(1, hid + vis), "drift_if_all_hidden_are_real": (hid + vis) / len(st),
                 "drift_lenient": vis / len(st)}
OUT["lenient"] = L

# ------------------------------------------------------------------ 5. fully enumerated repositories only
full = {r for r, v in repos.items() if v["fully_enumerated"] == "1"}
wf = lambda r: 1 if r in full else 0
E = {"repos": len(full)}
for k in "10":
    cs = [c for c in anch[k] if c["repo"] in full]
    d = drift_of(cs)
    E[LAB[k]] = {"drift": d["drift"], "violated": d["violated"], "anchored_at_head": d["anchored_at_head"], "break_rate": d["rate_per_100cy"],
                 "breaks": d["breaks"], "insync_share": insync_share(k, wf), "open_share": open_share(k, wf)}
rr = rates(wf)
E["context"]["invalidation_rate"], E["readme"]["invalidation_rate"] = rr["context_invalidation_rate"], rr["readme_invalidation_rate"]
OUT["enumerated"] = E

# ------------------------------------------------------------------ 6. drift by age: truncated and within cohort
ages = rows("drift_by_age.csv")
byfile = collections.defaultdict(list)
for a in ages:
    byfile[(a["repo"], a["file"])].append((float(a["age_days"]), int(a["n_born_valid"]), int(a["n_violated"])))


def at(obs, m):
    cur = [o for o in obs if o[0] <= m + 1e-9]
    return cur[-1][2] / cur[-1][1] if cur and cur[-1][1] > 0 else None


AG = {"all_files": [], "cohort_240": []}
cohort = {k: sorted(v) for k, v in byfile.items() if sorted(v)[-1][0] >= 240}
for m in (0, 30, 60, 90, 120, 180, 240):
    vals = collections.defaultdict(list)
    for (repo, _), obs in byfile.items():
        obs = sorted(obs)
        if obs[-1][0] >= m and at(obs, m) is not None:
            vals[repo].append(at(obs, m))
    keys = list(vals)
    allv = [v for k in keys for v in vals[k]]
    bs = [np.mean([v for i in rng.integers(0, len(keys), len(keys)) for v in vals[keys[i]]]) for _ in range(1000)]
    AG["all_files"].append({"age": m, "files": len(allv), "mean_drift": float(np.mean(allv)), "ci": np.percentile(bs, [2.5, 97.5]).tolist(),
                            "files_with_drift": int(sum(v > 0 for v in allv))})
    cv = [at(obs, m) for obs in cohort.values() if at(obs, m) is not None]
    AG["cohort_240"].append({"age": m, "files": len(cv), "mean_drift": float(np.mean(cv)), "files_with_drift": int(sum(v > 0 for v in cv))})
OUT["age"] = AG

# ------------------------------------------------------------------ 7. denominators (M1)
D = {}
for lab, sel in (("context", lambda r: r["is_ctx"] == "1"), ("readme", lambda r: r["is_ctx"] == "0"), ("AGENTS.md", lambda r: r["ftype"] == "AGENTS.md"),
                 ("CLAUDE.md", lambda r: r["ftype"] == "CLAUDE.md"), (".cursorrules", lambda r: r["ftype"] == ".cursorrules"),
                 ("copilot-instructions.md", lambda r: r["ftype"] == "copilot-instructions.md")):
    fs = [r for r in files if sel(r)]
    hit = sum(1 for r in fs if int(r["n_violated"]) > 0)
    withb = sum(1 for r in fs if int(r["n_born_valid"]) > 0)
    D[lab] = {"files": len(fs), "files_with_anchored": withb, "files_hit": hit, "share_of_all_files": hit / len(fs),
              "share_of_files_with_anchored": hit / withb, "wilson_all": wilson(hit, len(fs))}
OUT["denominators"] = D

# ------------------------------------------------------------------ 8. stratification by reference form and target type (round 2)
DOC_EXT = {"md", "mdx", "rst", "txt", "adoc", "markdown"}
ckey = {(c["repo"], c["file"], c["key"]): c for c in cons}


def form_of(c):
    if c["kind"] != "path":
        return "command"
    return "link" if c["sub"] == "link" else "code_span"


def ttype_of(c):
    if c["kind"] != "path":
        return "command"
    t = c["target"]
    if t.endswith("/"):
        return "directory"
    ext = t.rsplit("/", 1)[-1].rsplit(".", 1)[-1].lower() if "." in t.rsplit("/", 1)[-1] else ""
    return "doc_file" if ext in DOC_EXT else "other_file"


for r_ in rem:
    c = ckey[(r_["repo"], r_["file"], r_["key"])]
    r_["form"], r_["ttype"] = form_of(c), ttype_of(c)
for b in brk:
    c = ckey[(b["repo"], b["file"], b["key"])]
    b["form"], b["ttype"] = form_of(c), ttype_of(c)
FORMS = ["link", "code_span", "command"]
TTYPES = ["doc_file", "other_file", "directory", "command"]


def strat(attr, levels, kind):
    """Per-stratum shares and the stratified pooled difference (README minus context for in-sync, context minus README for open),
    with Cochran-Mantel-Haenszel weights n_c n_r / (n_c + n_r)."""
    def counts(w):
        d = {}
        for lv in levels:
            row = {}
            for k in "10":
                if kind == "insync":
                    y = sum(w(r["repo"]) for r in syncs[k] if r[attr] == lv)
                    n = y + sum(w(b["repo"]) for b in breaks[k] if b[attr] == lv)
                else:
                    bs_ = [b for b in breaks[k] if b[attr] == lv]
                    n = sum(w(b["repo"]) for b in bs_)
                    y = sum(w(b["repo"]) for b in bs_ if b["end"] == "open")
                row[k] = (y, n)
            d[lv] = row
        return d

    def pooled(w):
        d = counts(w)
        num = den = 0.0
        for lv in levels:
            (yc, nc), (yr, nr) = d[lv]["1"], d[lv]["0"]
            if nc > 0 and nr > 0:
                wt = nc * nr / (nc + nr)
                diff = (yr / nr - yc / nc) if kind == "insync" else (yc / nc - yr / nr)
                num += wt * diff
                den += wt
        return num / den if den else float("nan")

    d = counts(lambda r: 1)
    out = {"strata": {lv: {"context_n": d[lv]["1"][1], "context_share": d[lv]["1"][0] / d[lv]["1"][1] if d[lv]["1"][1] else None,
                           "readme_n": d[lv]["0"][1], "readme_share": d[lv]["0"][0] / d[lv]["0"][1] if d[lv]["0"][1] else None} for lv in levels}}
    for lv in levels:
        st = out["strata"][lv]
        if st["context_share"] is not None and st["readme_share"] is not None:
            st["diff"] = (st["readme_share"] - st["context_share"]) if kind == "insync" else (st["context_share"] - st["readme_share"])
    bs = [pooled((lambda w: (lambda r: w.get(r, 0)))(boot_weights())) for _ in range(B)]
    out["stratified_diff"] = {"est": pooled(lambda r: 1), "ci": np.nanpercentile(np.array(bs, float), [2.5, 97.5]).tolist()}

    def within(lv):
        def g(w):
            dd = counts(w)[lv]
            (yc, nc), (yr, nr) = dd["1"], dd["0"]
            if not nc or not nr:
                return float("nan")
            return (yr / nr - yc / nc) if kind == "insync" else (yc / nc - yr / nr)
        bsw = [g((lambda w: (lambda r: w.get(r, 0)))(boot_weights())) for _ in range(B)]
        return {"est": g(lambda r: 1), "ci": np.nanpercentile(np.array(bsw, float), [2.5, 97.5]).tolist()}

    for lv in levels:
        if out["strata"][lv]["context_n"] >= 20 and out["strata"][lv]["readme_n"] >= 20:
            out["strata"][lv]["diff_ci"] = within(lv)["ci"]
    return out


ST = {"composition_anchored": {LAB[k]: {f: float(np.mean([form_of(c) == f for c in anch[k]])) for f in FORMS} for k in "10"},
      "composition_target": {LAB[k]: {t: float(np.mean([ttype_of(c) == t for c in anch[k]])) for t in TTYPES} for k in "10"},
      "insync_by_form": strat("form", FORMS, "insync"), "open_by_form": strat("form", FORMS, "open"),
      "insync_by_target": strat("ttype", TTYPES, "insync"), "open_by_target": strat("ttype", TTYPES, "open")}
# rates within code spans
def rate_form(w, f):
    out = {}
    for k in "10":
        cs = [c for c in anch[k] if form_of(c) == f]
        ex = sum(w(c["repo"]) * c["exposure_days"] for c in cs) / 365.25
        nb = sum(w(b["repo"]) for b in breaks[k] if b["form"] == f)
        ns = sum(w(r["repo"]) for r in syncs[k] if r["form"] == f)
        out[LAB[k] + "_invalidation_rate"] = 100 * (nb + ns) / ex if ex else float("nan")
        out[LAB[k] + "_break_rate"] = 100 * nb / ex if ex else float("nan")
    out["invalidation_ratio"] = out["context_invalidation_rate"] / out["readme_invalidation_rate"]
    out["break_ratio"] = out["context_break_rate"] / out["readme_break_rate"]
    return out


ST["rates_code_span"] = paired(lambda w: rate_form(w, "code_span"), b=1000)
# contrast without links to documentation files (both artefacts)
nodoc = lambda x: not (x["form"] == "link" and x["ttype"] == "doc_file")
def no_doc_links(w):
    out = {}
    for k in "10":
        sy = sum(w(r["repo"]) for r in syncs[k] if nodoc(r)); br = sum(w(b["repo"]) for b in breaks[k] if nodoc(b))
        out[LAB[k] + "_insync"] = sy / (sy + br) if sy + br else float("nan")
        bs_ = [b for b in breaks[k] if nodoc(b)]
        den = sum(w(b["repo"]) for b in bs_)
        out[LAB[k] + "_open"] = sum(w(b["repo"]) for b in bs_ if b["end"] == "open") / den if den else float("nan")
    out["insync_diff"] = out["readme_insync"] - out["context_insync"]
    out["open_diff"] = out["context_open"] - out["readme_open"]
    return out
ST["without_links_to_doc_files"] = paired(no_doc_links)
OUT["form"] = ST

# ------------------------------------------------------------------ 9. within-repository sign split, bulk rewrites, at-risk counts, re-added keys
def sign_split(kind):
    pc, _ = per_repo("1", kind)
    pr, _ = per_repo("0", kind)
    both = sorted(set(pc) & set(pr))
    d = [(pr[r] - pc[r]) if kind == "insync" else (pc[r] - pr[r]) for r in both]
    pos, neg, tie = sum(x > 0 for x in d), sum(x < 0 for x in d), sum(x == 0 for x in d)
    return {"repos": len(both), "favours_headline_direction": pos, "opposite": neg, "ties": tie,
            "sign_test_p": float(stats.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else None}


OUT["within_repo"] = {"insync": sign_split("insync"), "open": sign_split("open")}
per_commit_removed = collections.Counter((r["repo"], r["file"], r["commit"]) for r in rem)
BULK = 10
bulk = {}
for k in "10":
    big = [r for r in syncs[k] if per_commit_removed[(r["repo"], r["file"], r["commit"])] >= BULK]
    small = len(syncs[k]) - len(big)
    bulk[LAB[k]] = {"in_sync": len(syncs[k]), "in_bulk_rewrites": len(big), "share_bulk": len(big) / len(syncs[k]),
                    "insync_share_without_bulk": small / (small + len(breaks[k]))}
bulk["diff_without_bulk"] = bulk["readme"]["insync_share_without_bulk"] - bulk["context"]["insync_share_without_bulk"]
def nobulk(w):
    o = {}
    for k in "10":
        sy = sum(w(r["repo"]) for r in syncs[k] if per_commit_removed[(r["repo"], r["file"], r["commit"])] < BULK)
        br = sum(w(b["repo"]) for b in breaks[k])
        o[LAB[k]] = sy / (sy + br) if sy + br else float("nan")
    return {"diff": o["readme"] - o["context"]}
bulk["diff_without_bulk_ci"] = paired(nobulk)["diff"]["ci"]
OUT["bulk_rewrites"] = bulk
AR = {}
for name, cs in (("context", anch["1"]), ("readme_entry_observed", [c for c in anch["0"] if c["left_truncated"] == "0"])):
    AR[name] = {}
    for m in (90, 180, 365):
        at_ = [c for c in cs if c["days"] >= m]
        AR[name][str(m)] = {"at_risk": len(at_), "files": len({(c["repo"], c["file"]) for c in at_}), "repos": len({c["repo"] for c in at_})}
    AR[name]["median_followup_days"] = float(np.median([c["days"] for c in cs]))
OUT["at_risk"] = AR
OUT["readded_keys"] = {LAB[k]: {"removed_while_valid_events": sum(1 for r in rem if r["is_ctx"] == k and r["type"] == "removal_valid"),
                                "of_which_key_live_at_head": sum(1 for r in rem if r["is_ctx"] == k and r["type"] == "removal_valid"
                                                                 and ckey[(r["repo"], r["file"], r["key"])]["live_head"] == "1")} for k in "10"}
live_ctx = [c for c in cons if c["is_ctx"] == "1" and c["live_head"] == "1"]
OUT["head_partition"] = {"head": len(live_ctx), "anchored": sum(1 for c in live_ctx if A(c)), "never_valid": sum(1 for c in live_ctx if c["ever_valid"] == "0"),
                         "entered_invalid_later_valid": sum(1 for c in live_ctx if not A(c) and c["ever_valid"] == "1"),
                         "lifetimes_all": sum(1 for c in cons if c["is_ctx"] == "1"), "lifetimes_not_anchored": sum(1 for c in cons if c["is_ctx"] == "1" and not A(c))}
OUT["bootstrap_resamples"] = {"default": B, "cumulative_incidence": 500, "entry_restricted_and_path_only_rates": 1000, "age_curve": 1000, "code_span_rates": 1000}

# ------------------------------------------------------------------ 10. internal AI-assisted spot check (not human, not external)
OUT["internal_ai_spot_check"] = {"source": "counts reported by the project's internal AI review loop in the internal development review. The raters were AI reviewers, not humans. "
                                 "Item-level labels are not available. Not used in the paper.",
                                 "constraints": {"n": 40, "genuine": 36}, "breaks": {"n": 36, "true": 28}}

json.dump(OUT, open(os.path.join(RES, "robustness.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
show = {k: OUT[k] for k in ("form", "within_repo", "bulk_rewrites", "at_risk", "readded_keys", "head_partition")}
print(json.dumps(show, indent=1, default=str))

#!/usr/bin/env python3
"""Stage 11: agreement and estimates from the two human rater sheets, and the LaTeX macros the paper prints.

Outputs
  results/human_validation.json
  ../manuscript/human_numbers.tex   one macro per human-derived number. While any required sheet is unfilled or
                                    unadjudicated, EVERY macro expands to a visible PENDING marker and the paper carries a draft banner.

Rules
  - Labels: yes / no / unsure. Kappa is computed on the three categories before adjudication.
  - An item is resolved when both raters give the same yes or no. Every other item (disagreement, or unsure by either rater)
    must appear in labelling/adjudicated.csv (id,column,label). An adjudicated "unsure" is excluded from the estimate and counted.
  - Stratified samples: population-weighted share, with a percentile interval from a bootstrap within strata (2,000 resamples).
  - Recall: per rater, weighted by lines over sampled lines per file, interval from a bootstrap over files. The paper reports the mean of
    the two raters and both values; agreement is Cohen's kappa on "line contains a repository reference" and exact agreement on counts.
  - Rename check (Sheet B, column break_cause): for every item whose resolved true_staleness is yes, each rater gives the cause of the break:
    deleted / moved_renamed / other (or unsure). Equal categories resolve; everything else goes to adjudicated.csv with column "break_cause".
    Shares are ratio estimates over strata, weighted by stratum population times the stratum's share of true breaks, with a bootstrap within strata.
Set S03_KIT to point at another kit folder (used by the end-to-end test).
"""
import csv, json, os, sys, collections
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s4_analyze import wilson

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.environ.get("S03_KIT") or os.path.join(ART, "labelling")
OUT_JSON = os.environ.get("S03_HUMAN_JSON") or os.path.join(ART, "results", "human_validation.json")
OUT_TEX = os.environ.get("S03_HUMAN_TEX") or os.path.join(os.path.dirname(ART), "manuscript", "human_numbers.tex")
YES, NO = {"yes", "y", "1", "true"}, {"no", "n", "0", "false"}
KINDS = ["path", "script", "target", "manifest", "dep"]
B, SEED = 2000, 20261005
CAUSES = ["deleted", "moved_renamed", "other"]
CAUSE_ALIAS = {"delete": "deleted", "removed": "deleted", "moved": "moved_renamed", "renamed": "moved_renamed", "move": "moved_renamed",
               "rename": "moved_renamed", "moved/renamed": "moved_renamed", "moved-renamed": "moved_renamed"}


def load(rater, name):
    return {r["id"]: r for r in csv.DictReader(open(os.path.join(KIT, rater, name + ".csv")))}


def key(name):
    return {r["id"]: r for r in csv.DictReader(open(os.path.join(KIT, "key", name + ".csv")))}


def norm(v):
    v = (v or "").strip().lower()
    if v not in YES | NO | {"", "unsure"}:
        raise ValueError("Invalid label: " + repr(v))
    return "yes" if v in YES else "no" if v in NO else v


def kappa(pairs):
    n = len(pairs)
    cats = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return po, ((po - pe) / (1 - pe) if pe < 1 else 1.0)


def adjudicated():
    p = os.path.join(KIT, "adjudicated.csv")
    return {(r["id"], r["column"]): (norm_cause if r["column"] == "break_cause" else norm)(r["label"]) for r in csv.DictReader(open(p))} if os.path.exists(p) else {}


def resolve(name, value_of, cols):
    """value_of(row) -> 'yes' / 'no' / 'unsure' / '' for one rater. Returns status dict and final labels."""
    a, b, adj = load("rater1", name), load("rater2", name), adjudicated()
    va, vb = {i: value_of(a[i]) for i in a}, {i: value_of(b[i]) for i in a}
    if any(not va[i] or not vb[i] for i in a):
        return {"status": "pending", "items": len(a), "filled_by_both": sum(1 for i in a if va[i] and vb[i])}, None
    po, kp = kappa([(va[i], vb[i]) for i in a])
    final, todo = {}, []
    for i in a:
        if va[i] == vb[i] and va[i] in ("yes", "no"):
            final[i] = va[i]
        elif (i, cols) in adj:
            final[i] = adj[(i, cols)]
        else:
            todo.append(i)
    st = {"status": "complete" if not todo else "needs adjudication", "items": len(a), "filled_by_both": len(a), "raw_agreement": po, "cohen_kappa": kp,
          "to_adjudicate": todo, "adjudicated": sum(1 for i in a if (i, cols) in adj and not (va[i] == vb[i] and va[i] in ("yes", "no"))),
          "final_unsure": sum(1 for v in final.values() if v not in ("yes", "no"))}
    return st, final


def strat_share(final, k, select=lambda r: True, rng=None):
    """Population-weighted share of yes over strata, with a bootstrap-within-strata interval. Unsure items are excluded."""
    groups = collections.defaultdict(list)
    pop = {}
    for i, v in final.items():
        if v in ("yes", "no") and select(k[i]):
            groups[k[i]["stratum"]].append(v == "yes")
            pop[k[i]["stratum"]] = int(k[i]["stratum_population"])
    if not groups:
        return None
    tot = sum(pop.values())
    est = sum(pop[s] * np.mean(g) for s, g in groups.items()) / tot
    bs = []
    for _ in range(B):
        bs.append(sum(pop[s] * np.mean(np.array(g)[rng.integers(0, len(g), len(g))]) for s, g in groups.items()) / tot)
    n = sum(len(g) for g in groups.values())
    y = sum(sum(g) for g in groups.values())
    return {"n": n, "yes": int(y), "weighted_share": float(est), "ci": np.percentile(bs, [2.5, 97.5]).tolist(),
            "by_stratum": {s: {"n": len(g), "yes": int(sum(g)), "share": float(np.mean(g)), "population": pop[s]} for s, g in groups.items()}}


def _recall_est(r, k, fset):
    """Recall of one rater over the files in fset (file -> bootstrap weight), weighted by lines over sampled lines."""
    tot_true = collections.Counter()
    tot_hit = collections.Counter()
    for i in k:
        f = (k[i]["repo"], k[i]["file"])
        if f not in fset:
            continue
        w = fset[f] * int(k[i]["file_lines"]) / int(k[i]["file_sampled"])
        for kd in KINDS:
            t = float(r[i]["true_" + kd])
            tot_true[kd] += w * t
            tot_hit[kd] += w * min(t, float(k[i]["tool_" + kd]))
    out = {kd: (tot_hit[kd] / tot_true[kd] if tot_true[kd] else None) for kd in KINDS}
    out["all"] = sum(tot_hit.values()) / sum(tot_true.values()) if sum(tot_true.values()) else None
    return out


def _recall_load(sheet):
    """Returns (a, b, k, files) or a pending dict. Same schema for R_recall (context files) and R_recall_readme (README files)."""
    if not all(os.path.exists(os.path.join(KIT, d, sheet + ".csv")) for d in ("rater1", "rater2", "key")):
        return {"status": "pending", "note": "sheet " + sheet + " is not in the labelling kit (rater1, rater2 and key folders)"}
    a, b, k = load("rater1", sheet), load("rater2", sheet), key(sheet)
    cols = ["true_" + x for x in KINDS] + ["tool_wrong"]
    if any((r[i][c] or "").strip() == "" for r in (a, b) for i in r for c in cols):
        return {"status": "pending", "note": "every true_* and tool_wrong cell needs a count (0 if none)"}
    files = sorted({(k[i]["repo"], k[i]["file"]) for i in k})
    return a, b, k, files


def recall(rng, sheet="R_recall", frame="uniform sample of all non-blank lines of 30 context files, weighted by lines over sampled lines"):
    loaded = _recall_load(sheet)
    if isinstance(loaded, dict):
        return loaded
    a, b, k, files = loaded
    one = {f: 1 for f in files}
    res = {"status": "complete", "frame": frame, "n_files": len(files), "n_lines": len(k)}
    per = []
    for name, r in (("rater1", a), ("rater2", b)):
        e = _recall_est(r, k, one)
        bs = []
        for _ in range(B):
            w = collections.Counter(files[j] for j in rng.integers(0, len(files), len(files)))
            v = _recall_est(r, k, w)["all"]
            if v is not None:
                bs.append(v)
        res[name] = {"recall": e, "ci_all": np.percentile(bs, [2.5, 97.5]).tolist() if bs else None,
                     "true_references_in_sample": sum(float(r[i]["true_" + kd]) for i in k for kd in KINDS)}
        per.append(e)
    res["mean_recall_all"] = float(np.mean([p["all"] for p in per if p["all"] is not None])) if all(p["all"] is not None for p in per) else None
    res["mean_recall_path"] = float(np.mean([p["path"] for p in per])) if all(p["path"] is not None for p in per) else None
    res["mean_ci_all"] = np.mean([res["rater1"]["ci_all"], res["rater2"]["ci_all"]], axis=0).tolist() if res["rater1"]["ci_all"] and res["rater2"]["ci_all"] else None
    has = lambda r, i: str(sum(float(r[i]["true_" + kd]) for kd in KINDS) > 0)
    po, kp = kappa([(has(a, i), has(b, i)) for i in k])
    res["agreement_line_has_reference"] = {"raw_agreement": po, "cohen_kappa": kp}
    res["exact_count_agreement"] = float(np.mean([all(float(a[i]["true_" + kd]) == float(b[i]["true_" + kd]) for kd in KINDS) for i in k]))
    res["tool_wrong_mean"] = float(np.mean([sum(float(r[i]["tool_wrong"]) for i in k) for r in (a, b)]))
    return res


def recall_difference(rng):
    """Context-file recall minus README recall (mean of the two raters), bootstrap over files, drawn independently per artefact
    because the two samples contain different files. Needs both recall sheets complete."""
    lc, lr = _recall_load("R_recall"), _recall_load("R_recall_readme")
    if isinstance(lc, dict) or isinstance(lr, dict):
        return {"status": "pending"}
    def mean_recall(ld, fset):
        a, b, k, _ = ld
        v = [_recall_est(r, k, fset)["all"] for r in (a, b)]
        return None if any(x is None for x in v) else float(np.mean(v))
    est = mean_recall(lc, {f: 1 for f in lc[3]}) - mean_recall(lr, {f: 1 for f in lr[3]})
    d = []
    for _ in range(B):
        wc = collections.Counter(lc[3][j] for j in rng.integers(0, len(lc[3]), len(lc[3])))
        wr = collections.Counter(lr[3][j] for j in rng.integers(0, len(lr[3]), len(lr[3])))
        x, y = mean_recall(lc, wc), mean_recall(lr, wr)
        if x is not None and y is not None:
            d.append(x - y)
    return {"status": "complete", "est_context_minus_readme": est, "ci": np.percentile(d, [2.5, 97.5]).tolist() if d else None}


def norm_cause(v):
    v = (v or "").strip().lower()
    v = CAUSE_ALIAS.get(v, v)
    if v not in set(CAUSES) | {"", "unsure"}:
        raise ValueError("Invalid break_cause: " + repr(v))
    return v


def cause_block(final_b, k, rng):
    """Cause of true breaks (Sheet B, column break_cause). Needs the resolved true_staleness labels of Sheet B."""
    if final_b is None:
        return {"status": "pending", "note": "Sheet B is not resolved yet"}
    a, b, adj = load("rater1", "B_breaks"), load("rater2", "B_breaks"), adjudicated()
    if not a or "break_cause" not in next(iter(a.values())) or "break_cause" not in next(iter(b.values())):
        return {"status": "pending", "note": "column break_cause is missing in a rater sheet (run add_break_cause_column.py)"}
    ids = [i for i, v in final_b.items() if v == "yes"]
    va = {i: norm_cause(a[i]["break_cause"]) for i in ids}
    vb = {i: norm_cause(b[i]["break_cause"]) for i in ids}
    la = {i: norm(a[i]["true_staleness"]) for i in ids}
    lb = {i: norm(b[i]["true_staleness"]) for i in ids}
    # a rater who answered yes must give a cause; a rater who answered no or unsure may leave it empty
    missing = [i for i in ids if (la[i] == "yes" and not va[i]) or (lb[i] == "yes" and not vb[i])]
    if missing:
        return {"status": "pending", "items": len(ids), "missing_cause_for": missing}
    pairs = [(va[i], vb[i]) for i in ids if va[i] and vb[i]]
    po, kp = kappa(pairs) if pairs else (None, None)
    final, todo = {}, []
    for i in ids:
        if va[i] == vb[i] and va[i] in CAUSES:
            final[i] = va[i]
        elif (i, "break_cause") in adj:
            final[i] = norm_cause(adj[(i, "break_cause")])
        else:
            todo.append(i)
    res = {"status": "complete" if not todo else "needs adjudication", "items": len(ids), "raw_agreement": po, "cohen_kappa": kp, "to_adjudicate": todo,
           "adjudicated": sum(1 for i in ids if (i, "break_cause") in adj and not (va[i] == vb[i] and va[i] in CAUSES)),
           "final_unsure": sum(1 for v in final.values() if v not in CAUSES)}
    if todo:
        return res
    # per artefact: stratum -> list of (is_true_break, cause); false breaks (final no) count in the stratum size, unsure causes are dropped
    def groups(art):
        g, pop = collections.defaultdict(list), {}
        for i, v in final_b.items():
            if k[i]["artefact"] != art or v not in ("yes", "no"):
                continue
            if v == "yes" and final[i] not in CAUSES:
                continue
            g[k[i]["stratum"]].append((v == "yes", final.get(i)))
            pop[k[i]["stratum"]] = int(k[i]["stratum_population"])
        return g, pop

    def share(g, pop, cause, idx=None):
        num = den = 0.0
        for s, items in g.items():
            it = items if idx is None else [items[j] for j in idx[s]]
            n = len(it)
            num += pop[s] * sum(1 for y, c in it if y and c == cause) / n
            den += pop[s] * sum(1 for y, c in it if y) / n
        return num / den if den else None

    for art in ("context", "readme"):
        g, pop = groups(art)
        res[art] = {"true_breaks_in_sample": sum(1 for it in g.values() for y, _ in it if y), "items_in_strata": sum(len(it) for it in g.values())}
        for cause in CAUSES:
            bs = [x for x in (share(g, pop, cause, {s: rng.integers(0, len(it), len(it)) for s, it in g.items()}) for _ in range(B)) if x is not None]
            res[art][cause] = {"share": share(g, pop, cause), "ci": np.percentile(bs, [2.5, 97.5]).tolist() if bs else None,
                               "count": sum(1 for it in g.values() for y, c in it if y and c == cause)}
    gc = groups("context")
    gr = groups("readme")
    d = []
    for _ in range(B):
        x = share(gc[0], gc[1], "moved_renamed", {s: rng.integers(0, len(it), len(it)) for s, it in gc[0].items()})
        y = share(gr[0], gr[1], "moved_renamed", {s: rng.integers(0, len(it), len(it)) for s, it in gr[0].items()})
        if x is not None and y is not None:
            d.append(x - y)
    res["difference_context_minus_readme_moved"] = {"est": res["context"]["moved_renamed"]["share"] - res["readme"]["moved_renamed"]["share"],
                                                    "ci": np.percentile(d, [2.5, 97.5]).tolist()}
    return res


def main():
    rng = np.random.default_rng(SEED)
    out, finals = {}, {}
    rng_c = np.random.default_rng(SEED + 1)
    one = lambda col: (lambda row: norm(row[col]))
    both = lambda row: ("" if not norm(row["target_invalidated"]) or not norm(row["reference_updated"]) else
                        "yes" if norm(row["target_invalidated"]) == norm(row["reference_updated"]) == "yes" else
                        "unsure" if "unsure" in (norm(row["target_invalidated"]), norm(row["reference_updated"])) and "no" not in (norm(row["target_invalidated"]), norm(row["reference_updated"])) else "no")
    for name, vf, col in (("A_extraction", one("is_repo_reference"), "is_repo_reference"), ("B_breaks", one("true_staleness"), "true_staleness"),
                          ("S_insync", both, "in_sync"), ("L_lenient", one("matched_is_intended"), "matched_is_intended")):
        st, final = resolve(name, vf, col)
        out[name] = st
        finals[name] = final
        if st["status"] != "complete":
            continue
        k = key(name)
        if name == "A_extraction":
            st["all"] = strat_share(final, k, rng=rng)
            st["anchored"] = strat_share(final, k, lambda r: r["stratum"].startswith("anchored"), rng)
            st["anchored_violated"] = strat_share(final, k, lambda r: r["stratum"] == "anchored_violated", rng)
        elif name in ("B_breaks", "S_insync"):
            for art in ("context", "readme"):
                st[art] = strat_share(final, k, lambda r, art=art: r["artefact"] == art, rng)
            if st["context"] and st["readme"]:
                # interval of the difference from independent within-stratum bootstraps
                def boot(art):
                    g = collections.defaultdict(list)
                    pop = {}
                    for i, v in final.items():
                        if v in ("yes", "no") and k[i]["artefact"] == art:
                            g[k[i]["stratum"]].append(v == "yes")
                            pop[k[i]["stratum"]] = int(k[i]["stratum_population"])
                    tot = sum(pop.values())
                    return np.array([sum(pop[s] * np.mean(np.array(x)[rng.integers(0, len(x), len(x))]) for s, x in g.items()) / tot for _ in range(B)])
                d = boot("context") - boot("readme")
                st["difference_context_minus_readme"] = {"est": st["context"]["weighted_share"] - st["readme"]["weighted_share"], "ci": np.percentile(d, [2.5, 97.5]).tolist()}
        else:
            vals = [v == "yes" for v in final.values() if v in ("yes", "no")]
            st["intended"] = {"n": len(vals), "yes": int(sum(vals)), "share": float(np.mean(vals)), "wilson": wilson(int(sum(vals)), len(vals))}
    out["R_recall"] = recall(rng)
    out["R_recall_readme"] = recall(np.random.default_rng(SEED + 2), "R_recall_readme",
                                    "uniform sample of all non-blank lines of root README files, weighted by lines over sampled lines")
    out["R_recall_difference"] = recall_difference(np.random.default_rng(SEED + 3))
    out["B_cause"] = cause_block(finals.get("B_breaks") if out["B_breaks"]["status"] == "complete" else None, key("B_breaks"), rng_c)
    ver = os.path.join(KIT, "author_verification.txt")
    out["author_verification"] = open(ver).read().strip() if os.path.exists(ver) else None
    required = ["A_extraction", "B_breaks", "S_insync", "L_lenient", "R_recall"]
    done = all(out[n]["status"] == "complete" for n in required + ["B_cause"]) and bool(out["author_verification"])
    out["complete"] = done
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(out, open(OUT_JSON, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    # ------------------------------------------------------------ LaTeX macros
    M = {}
    pc = lambda x, d=0: f"{100 * x:.{d}f}"
    ci = lambda c, d=0: f"{100 * c[0]:.{d}f} to {100 * c[1]:.{d}f}"
    if done:
        A, Bk, S, L, R = (out[n] for n in required)
        M.update({"hPrecA": pc(A["all"]["weighted_share"]), "hPrecACI": ci(A["all"]["ci"]), "hPrecAAnch": pc(A["anchored"]["weighted_share"]),
                  "hPrecAAnchCI": ci(A["anchored"]["ci"]), "hPrecAViol": pc(A["anchored_violated"]["weighted_share"]), "hPrecAViolCI": ci(A["anchored_violated"]["ci"]),
                  "hKappaA": f"{A['cohen_kappa']:.2f}", "hNA": A["items"],
                  "hPrecBCtx": pc(Bk["context"]["weighted_share"]), "hPrecBCtxCI": ci(Bk["context"]["ci"]), "hPrecBRd": pc(Bk["readme"]["weighted_share"]),
                  "hPrecBRdCI": ci(Bk["readme"]["ci"]), "hPrecBDiff": pc(Bk["difference_context_minus_readme"]["est"]), "hPrecBDiffCI": ci(Bk["difference_context_minus_readme"]["ci"]),
                  "hKappaB": f"{Bk['cohen_kappa']:.2f}", "hNB": Bk["items"],
                  "hPrecSCtx": pc(S["context"]["weighted_share"]), "hPrecSCtxCI": ci(S["context"]["ci"]), "hPrecSRd": pc(S["readme"]["weighted_share"]),
                  "hPrecSRdCI": ci(S["readme"]["ci"]), "hPrecSDiff": pc(S["difference_context_minus_readme"]["est"]), "hPrecSDiffCI": ci(S["difference_context_minus_readme"]["ci"]),
                  "hKappaS": f"{S['cohen_kappa']:.2f}", "hNS": S["items"],
                  "hLenient": pc(L["intended"]["share"]), "hLenientCI": ci(L["intended"]["wilson"]), "hKappaL": f"{L['cohen_kappa']:.2f}", "hNL": L["items"],
                  "hRecall": pc(R["mean_recall_all"]), "hRecallCI": ci(R["mean_ci_all"]), "hRecallPath": pc(R["mean_recall_path"]),
                  "hRecallROne": pc(R["rater1"]["recall"]["all"]), "hRecallRTwo": pc(R["rater2"]["recall"]["all"]),
                  "hKappaR": f"{R['agreement_line_has_reference']['cohen_kappa']:.2f}",
                  "hNAdjudicated": sum(out[n].get("adjudicated", 0) for n in required[:4]), "hNUnsure": sum(out[n].get("final_unsure", 0) for n in required[:4]),
                  "hKappaC": f"{out['B_cause']['cohen_kappa']:.2f}", "hNC": out["B_cause"]["items"], "hNAdjudicatedCause": out["B_cause"]["adjudicated"],
                  "hRenCtx": pc(out["B_cause"]["context"]["moved_renamed"]["share"]), "hRenCtxCI": ci(out["B_cause"]["context"]["moved_renamed"]["ci"]),
                  "hRenRd": pc(out["B_cause"]["readme"]["moved_renamed"]["share"]), "hRenRdCI": ci(out["B_cause"]["readme"]["moved_renamed"]["ci"]),
                  "hRenDiff": pc(out["B_cause"]["difference_context_minus_readme_moved"]["est"]), "hRenDiffCI": ci(out["B_cause"]["difference_context_minus_readme_moved"]["ci"]),
                  "hDelCtx": pc(out["B_cause"]["context"]["deleted"]["share"]), "hDelRd": pc(out["B_cause"]["readme"]["deleted"]["share"]),
                  "hOthCtx": pc(out["B_cause"]["context"]["other"]["share"]), "hOthRd": pc(out["B_cause"]["readme"]["other"]["share"]),
                  "hNRenCtx": out["B_cause"]["context"]["moved_renamed"]["count"], "hNRenRd": out["B_cause"]["readme"]["moved_renamed"]["count"],
                  "hAuthorVerification": out["author_verification"].replace("%", "\\%").replace("&", "\\&").replace("_", "\\_")})
    RC, RR, RD = out["R_recall"], out["R_recall_readme"], out["R_recall_difference"]
    if RC["status"] == "complete":
        M.update({"hNRecallFilesCtx": RC["n_files"], "hNRecallLinesCtx": RC["n_lines"]})
    if RR["status"] == "complete":
        M.update({"hRecallRd": pc(RR["mean_recall_all"]), "hRecallRdCI": ci(RR["mean_ci_all"]), "hRecallRdPath": pc(RR["mean_recall_path"]),
                  "hRecallRdROne": pc(RR["rater1"]["recall"]["all"]), "hRecallRdRTwo": pc(RR["rater2"]["recall"]["all"]),
                  "hKappaRRd": f"{RR['agreement_line_has_reference']['cohen_kappa']:.2f}",
                  "hNRecallFilesRd": RR["n_files"], "hNRecallLinesRd": RR["n_lines"]})
    if RD["status"] == "complete":
        M.update({"hRecallDiff": pc(RD["est_context_minus_readme"]), "hRecallDiffCI": ci(RD["ci"])})
    new_names = ["hRecallRd", "hRecallRdCI", "hRecallRdPath", "hRecallRdROne", "hRecallRdRTwo", "hKappaRRd", "hNRecallFilesRd", "hNRecallLinesRd",
                 "hNRecallFilesCtx", "hNRecallLinesCtx", "hRecallDiff", "hRecallDiffCI"]
    names = ["hPrecA", "hPrecACI", "hPrecAAnch", "hPrecAAnchCI", "hPrecAViol", "hPrecAViolCI", "hKappaA", "hNA", "hPrecBCtx", "hPrecBCtxCI", "hPrecBRd", "hPrecBRdCI",
             "hPrecBDiff", "hPrecBDiffCI", "hKappaB", "hNB", "hPrecSCtx", "hPrecSCtxCI", "hPrecSRd", "hPrecSRdCI", "hPrecSDiff", "hPrecSDiffCI", "hKappaS", "hNS",
             "hLenient", "hLenientCI", "hKappaL", "hNL", "hRecall", "hRecallCI", "hRecallPath", "hRecallROne", "hRecallRTwo", "hKappaR", "hNAdjudicated", "hNUnsure",
             "hKappaC", "hNC", "hNAdjudicatedCause", "hRenCtx", "hRenCtxCI", "hRenRd", "hRenRdCI", "hRenDiff", "hRenDiffCI", "hDelCtx", "hDelRd", "hOthCtx", "hOthRd",
             "hNRenCtx", "hNRenRd", "hAuthorVerification"] + new_names
    with open(OUT_TEX, "w") as f:
        f.write("% Generated by the labelling agreement script. Do not edit by hand.\n")
        f.write("\\newcommand{\\PENDING}{\\textcolor{red}{\\textbf{[PENDING]}}}\n")
        if done:
            f.write("\\newcommand{\\hDraftBanner}{}\n")
        else:
            f.write("\\newcommand{\\hDraftBanner}{\\noindent\\fcolorbox{red}{white}{\\parbox{0.95\\linewidth}{\\textcolor{red}{\\textbf{DRAFT, NOT FOR SUBMISSION.} "
                    "Two-rater human labelling and author verification are not done. Every figure marked [PENDING] is missing.}}}\\par\\smallskip}\n")
        for n in names:
            value = M.get(n, "\\PENDING")
            f.write(f"\\newcommand{{\\{n}}}{{{value}}}\n")
    print(json.dumps({k: (v.get("status") if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
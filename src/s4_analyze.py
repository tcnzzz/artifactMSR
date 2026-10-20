#!/usr/bin/env python3
"""Stage 4: turn the mined per-repository timelines into the result tables behind every paper number.

Reads <cache>/mined/*.json.gz, writes artifact/results/*.csv and summary.json.
"""
import gzip, glob, json, os, sys, csv, math, re, collections, bisect, random
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as RL
import compiler as K

CACHE = os.environ.get("S03_CACHE") or os.path.expanduser("~/.cache/context-rot-study/S03")
if not os.path.isdir(os.path.join(CACHE, "mined")):  # fall back to the copy shipped inside the package
    CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
DAY = 86400.0
B = 2000
SEED = 20261003
FTYPE = {"AGENTS.md": "AGENTS.md", "CLAUDE.md": "CLAUDE.md", ".claude/CLAUDE.md": "CLAUDE.md", ".cursorrules": ".cursorrules",
         ".github/copilot-instructions.md": "copilot-instructions.md", "README.md": "README.md"}
CC_RX = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|tests|build|ci|chore|revert|deps|release)(\([^)]+\))?!?: \S")
CC_RULE = re.compile(r"conventional[ \-]commits?", re.I)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def km(durations, events):
    """Kaplan-Meier estimator. Returns (times, survival) arrays at event times."""
    d = np.asarray(durations, float)
    e = np.asarray(events, bool)
    order = np.argsort(d)
    d, e = d[order], e[order]
    times, surv, s = [], [], 1.0
    n = len(d)
    i = 0
    while i < n:
        t = d[i]
        j = i
        deaths = 0
        while j < n and d[j] == t:
            deaths += e[j]
            j += 1
        if deaths:
            s *= 1 - deaths / (n - i)
            times.append(t)
            surv.append(s)
        i = j
    return np.array(times), np.array(surv)


def km_at(times, surv, t):
    k = np.searchsorted(times, t, side="right") - 1
    return 1.0 if k < 0 else float(surv[k])


def km_median(times, surv):
    idx = np.where(surv <= 0.5)[0]
    return float(times[idx[0]]) if len(idx) else float("nan")


def cluster_boot(groups, stat, rng, b=B):
    """groups: dict cluster -> payload. stat: list of payloads -> float or tuple. Percentile interval."""
    keys = list(groups)
    out = []
    for _ in range(b):
        samp = [groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))]
        out.append(stat(samp))
    arr = np.array(out, float)
    return np.nanpercentile(arr, [2.5, 97.5], axis=0)


def load():
    for f in sorted(glob.glob(os.path.join(CACHE, "mined", "*.json.gz"))):
        with gzip.open(f, "rt") as fh:
            yield json.load(fh)


def main():
    os.makedirs(RES, exist_ok=True)
    rng = np.random.default_rng(SEED)
    funnel = json.load(open(os.path.join(CACHE, "search", "sample.json")))["funnel"]
    skipped = collections.Counter()
    file_rows, cons_rows, break_rows, sync_rows, age_rows = [], [], [], [], []
    rule_rows, core_rows, cc_rows, repo_rows = [], [], [], []
    n_mined = 0
    for d in load():
        if "skip" in d:
            skipped["error" if d["skip"].startswith("error") else d["skip"]] += 1
            continue
        n_mined += 1
        repo = d["repo"]
        snaps = d["snaps"]
        snap_ts = {s: ts for s, ts, _ in snaps}
        snap_list = [s for s, _, _ in snaps]
        head_idx, head_ts = snaps[-1][0], snaps[-1][1]
        ev_by = collections.defaultdict(list)
        for e in d["events"]:
            ev_by[(e["file"], e["key"], e["type"])].append(e)
        repo_rows.append({"repo": repo, "stars": d["meta"].get("stargazerCount"), "language": (d["meta"].get("primaryLanguage") or {}).get("name") or "none",
                          "n_first_parent_commits": d["n_chain"], "window_commits": d["n_chain"] - d["t0"], "n_snapshots": len(snaps),
                          "fully_enumerated": int(d["fully_enumerated"]), "window_days": round((head_ts - snaps[0][1]) / DAY, 1),
                          "ctx_files": ";".join(p for p in d["files"] if p != "README.md"),
                          "window_commits_all": sum(1 for i, c in enumerate(d["commits"], d["commits_offset"]) if i >= d["t0"]),
                          "window_agent_commits": sum(c[3] for i, c in enumerate(d["commits"], d["commits_offset"]) if i >= d["t0"])})
        for p, fd in d["files"].items():
            ftype = FTYPE[p]
            is_ctx = p != "README.md"
            vers = [v for v in fd["versions"] if v[0] >= d["t0"]] if not is_ctx else fd["versions"]
            if not fd["versions"]:
                continue
            birth_ts = fd["versions"][0][1] if is_ctx else snaps[0][1]
            last_edit_ts = fd["versions"][-1][1]
            n_live = n_bv = n_viol = n_never = n_viol_strict = n_bv_strict = 0
            file_snaps = sorted({s for c in fd["constraints"].values() for s, _ in c["obs"]})
            per_age = collections.defaultdict(lambda: [0, 0])   # snap -> [born-valid live, violated]
            for key, c in fd["constraints"].items():
                obs = c["obs"]
                s0, c0 = obs[0]
                born_valid = c0 > 0
                live_head = obs[-1][0] == head_idx
                ever_valid = any(x > 0 for _, x in obs)
                t_first = snap_ts[s0]
                # first break and exposure
                first_break_ts, exposure, nbreaks = None, 0.0, 0
                brk = sorted(ev_by.get((p, key, "break"), []), key=lambda e: e["idx"])
                episodes = []
                for i, ((a, ca), (b, cb)) in enumerate(zip(obs, obs[1:])):
                    if ca > 0:
                        exposure += max(0.0, snap_ts[b] - snap_ts[a])
                    if ca > 0 and cb == 0:
                        e = next((e for e in brk if a < e["idx"] <= b), None)
                        bts = e["ts"] if e else snap_ts[b]
                        nbreaks += 1
                        if first_break_ts is None and born_valid:
                            first_break_ts = bts
                        # how does the episode end
                        end_ts, how = None, None
                        for (s2, c2) in obs[i + 2:]:
                            if c2 > 0:
                                end_ts, how = snap_ts[s2], "repo_repair"
                                break
                        if how is None:
                            if live_head:
                                end_ts, how = head_ts, "open"
                            else:
                                nxt = bisect.bisect_right(snap_list, obs[-1][0])
                                end_ts = snaps[nxt][1] if nxt < len(snaps) else head_ts
                                how = "edit_repair"
                        end_idx = None
                        if how == "repo_repair":
                            end_idx = next(s2 for (s2, c2) in obs[i + 2:] if c2 > 0)
                        elif how == "edit_repair":
                            nxt2 = bisect.bisect_right(snap_list, obs[-1][0])
                            end_idx = snaps[nxt2][0] if nxt2 < len(snaps) else None
                        rewritten = ""
                        if how == "edit_repair" and is_ctx and end_idx is not None and c["kind"] == "path":
                            oid = dict(fd["version_oids"]).get(end_idx)
                            base = c["target"].rstrip("/").rsplit("/", 1)[-1]
                            rewritten = 0
                            if oid and fd["texts"].get(oid):
                                for nc in K.compile_text(fd["texts"][oid]):
                                    if nc.kind == "path" and nc.key != key and nc.target.rstrip("/").rsplit("/", 1)[-1] == base:
                                        o2 = dict(fd["constraints"].get(nc.key, {}).get("obs", []))
                                        if o2.get(end_idx, 0) > 0:
                                            rewritten = 1
                        episodes.append((bts, end_ts, how, e, end_idx, rewritten))
                for bts, end_ts, how, e, end_idx, rewritten in episodes:
                    break_rows.append({"repo": repo, "file": p, "ftype": ftype, "is_ctx": int(is_ctx), "key": key, "kind": c["kind"],
                                       "sub": c["sub"], "target": c["target"], "born_valid": int(born_valid), "break_ts": bts,
                                       "commit": e["commit"] if e else "", "exact": int(bool(e and e["exact"])),
                                       "ctx_touched_in_break_commit": int(bool(e and e["ctx_touched"])),
                                       "agent_commit": (d["commits"][e["idx"] - d["commits_offset"]][3] if e and e["idx"] >= d["commits_offset"] else ""),
                                       "end": how, "days_broken": round(max(0.0, end_ts - bts) / DAY, 3),
                                       "commits_broken": (end_idx - e["idx"]) if (e and end_idx is not None) else "",
                                       "days_before_head": round((head_ts - bts) / DAY, 3), "rewritten": rewritten,
                                       "is_bare": int(c["kind"] == "path" and "/" not in c["target"].rstrip("/")), "raw": c["raw"]})
                removed = not live_head
                if removed:
                    nxt = bisect.bisect_right(snap_list, obs[-1][0])
                    end_obs_ts = snaps[nxt][1] if nxt < len(snaps) else head_ts
                else:
                    end_obs_ts = head_ts
                dur = (first_break_ts - t_first) if first_break_ts is not None else (end_obs_ts - t_first)
                if first_break_ts is not None:
                    terminal = "break"
                elif removed:
                    terminal = "sync_removal" if ev_by.get((p, key, "sync_removal")) else "removal_valid"
                else:
                    terminal = "censored"
                cons_rows.append({"repo": repo, "file": p, "ftype": ftype, "is_ctx": int(is_ctx), "key": key, "kind": c["kind"], "sub": c["sub"],
                                  "target": c["target"], "born_code": c0, "born_valid": int(born_valid), "ever_valid": int(ever_valid),
                                  "left_truncated": int((not is_ctx) and s0 == snaps[0][0]),
                                  "in_first_version": int(is_ctx and s0 == fd["versions"][0][0]),
                                  "live_head": int(live_head), "head_code": obs[-1][1] if live_head else "",
                                  "first_ts": t_first, "broke": int(first_break_ts is not None),
                                  "days_to_break_or_censor": round(max(0.0, dur) / DAY, 3),
                                  "exposure_days": round(exposure / DAY, 3), "n_breaks": nbreaks, "terminal": terminal,
                                  "is_bare": int(c["kind"] == "path" and "/" not in c["target"].rstrip("/")),
                                  "is_dir": int(c["kind"] == "path" and c["target"].endswith("/")), "line": c["line"], "raw": c["raw"]})
                for typ in ("sync_removal", "removal_valid", "removal_broken"):
                    for e in ev_by.get((p, key, typ), []):
                        sync_rows.append({"repo": repo, "file": p, "ftype": ftype, "is_ctx": int(is_ctx), "key": key, "kind": c["kind"],
                                          "type": typ, "ts": e["ts"], "commit": e["commit"], "born_valid": int(born_valid)})
                if live_head:
                    n_live += 1
                    if born_valid:
                        n_bv += 1
                        n_viol += obs[-1][1] == 0
                    if c0 == 1:
                        n_bv_strict += 1
                        n_viol_strict += obs[-1][1] != 1
                    if not ever_valid:
                        n_never += 1
                if born_valid and is_ctx:
                    for s, code in obs:
                        per_age[s][0] += 1
                        per_age[s][1] += code == 0
            if is_ctx:
                for s, (nb, nv) in per_age.items():
                    age_rows.append({"repo": repo, "file": p, "ftype": ftype, "age_days": round((snap_ts[s] - birth_ts) / DAY, 2), "n_born_valid": nb, "n_violated": nv})
            file_rows.append({"repo": repo, "file": p, "ftype": ftype, "is_ctx": int(is_ctx), "n_versions": len(fd["versions"]),
                              "age_days": round((head_ts - birth_ts) / DAY, 1), "days_since_edit": round((head_ts - last_edit_ts) / DAY, 1),
                              "bytes": fd["head_bytes"], "n_constraints": n_live, "n_born_valid": n_bv, "n_violated": n_viol,
                              "n_never_valid": n_never, "n_born_valid_strict": n_bv_strict, "n_violated_strict": n_viol_strict,
                              "drift": round(n_viol / n_bv, 4) if n_bv else ""})
            # ---- rule consistency on the head version
            if is_ctx and fd["head_text"]:
                rs, ax = RL.extract_rules(fd["head_text"])
                forms = collections.Counter(r["form"] for r in rs)
                clauses = [r["clause"] for r in rs]
                sat = RL.satisfiable(clauses + ax) if rs else True
                horn_sat = RL.satisfiable([c for c in clauses if RL.is_horn(c)] + ax) if rs else True
                rule_rows.append({"repo": repo, "file": p, "ftype": ftype, "n_rules": len(rs), "unit_pos": forms["unit+"], "unit_neg": forms["unit-"],
                                  "horn_definite": forms["horn-definite"], "horn_negative": forms["horn-negative"], "choice": forms["choice"],
                                  "unit_pos_cmd": sum(1 for r in rs if r["form"] == "unit+" and r["src"] == "cmd"), "n_axioms": len(ax), "satisfiable": int(sat), "all_horn": int(forms["choice"] == 0)})
                if not sat:
                    for ci, core in enumerate(RL.all_cores(clauses, ax)):
                        for cl in core:
                            r = next(r for r in rs if r["clause"] == cl)
                            core_rows.append({"repo": repo, "file": p, "core": ci, "core_size": len(core), "form": r["form"], "src": r["src"],
                                              "clause": " | ".join(s + a for s, a in cl), "line": r["line"], "text": r["text"]})
            # ---- compliance with a stated commit-message convention
            if is_ctx:
                intro = None
                for v, oid in fd["version_oids"]:
                    if CC_RULE.search(fd["texts"].get(oid, "")):
                        intro = v
                        break
                off = d["commits_offset"]
                commits = d["commits"]
                cut = intro if intro is not None else fd["versions"][0][0]
                pre = [c for i, c in enumerate(commits, off) if i < cut and not c[1]]
                post = [c for i, c in enumerate(commits, off) if i >= cut and not c[1]]
                cc = lambda cs: sum(1 for c in cs if CC_RX.match(c[2]))
                post_ag = [c for c in post if c[3]]
                post_hu = [c for c in post if not c[3]]
                cc_rows.append({"repo": repo, "file": p, "has_rule": int(intro is not None), "rule_at_creation": int(intro == fd["versions"][0][0]) if intro is not None else "",
                                "n_pre": len(pre), "cc_pre": cc(pre), "n_post": len(post), "cc_post": cc(post),
                                "n_post_agent": len(post_ag), "cc_post_agent": cc(post_ag), "n_post_other": len(post_hu), "cc_post_other": cc(post_hu)})

    def dump(name, rows):
        if not rows:
            open(os.path.join(RES, name), "w").write("")
            return
        with open(os.path.join(RES, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    dump("repos.csv", repo_rows)
    dump("files.csv", file_rows)
    dump("constraints.csv", cons_rows)
    dump("breaks.csv", break_rows)
    dump("removals.csv", sync_rows)
    dump("drift_by_age.csv", age_rows)
    dump("rules.csv", rule_rows)
    dump("inconsistency_cores.csv", core_rows)
    dump("commit_convention.csv", cc_rows)

    # ------------------------------------------------------------------ summary statistics
    S = {"funnel": dict(funnel, mined_ok=n_mined, skipped=dict(skipped))}
    ctx_files = [r for r in file_rows if r["is_ctx"]]
    S["corpus"] = {
        "repos": n_mined, "context_files": len(ctx_files), "readme_files": sum(1 for r in file_rows if not r["is_ctx"]),
        "files_by_type": dict(collections.Counter(r["ftype"] for r in ctx_files)),
        "median_stars": float(np.median([r["stars"] for r in repo_rows])),
        "stars_iqr": [float(x) for x in np.percentile([r["stars"] for r in repo_rows], [25, 75])],
        "languages_top": collections.Counter(r["language"] for r in repo_rows).most_common(8),
        "median_versions": float(np.median([r["n_versions"] for r in ctx_files])),
        "median_age_days": float(np.median([r["age_days"] for r in ctx_files])),
        "age_iqr": [float(x) for x in np.percentile([r["age_days"] for r in ctx_files], [25, 75])],
        "share_single_version": float(np.mean([r["n_versions"] == 1 for r in ctx_files])),
        "median_days_since_edit": float(np.median([r["days_since_edit"] for r in ctx_files])),
        "total_snapshots": int(sum(r["n_snapshots"] for r in repo_rows)),
        "fully_enumerated_repos": int(sum(r["fully_enumerated"] for r in repo_rows)),
        "constraint_lifetimes_ctx": sum(1 for c in cons_rows if c["is_ctx"]),
        "constraint_lifetimes_readme": sum(1 for c in cons_rows if not c["is_ctx"]),
    }

    # ---- RQ1 head drift
    def head_stats(rows):
        withc = [r for r in rows if r["n_constraints"] > 0]
        withbv = [r for r in rows if r["n_born_valid"] > 0]
        k = sum(r["n_violated"] for r in withbv)
        n = sum(r["n_born_valid"] for r in withbv)
        any_v = sum(1 for r in withbv if r["n_violated"] > 0)
        by_repo = collections.defaultdict(list)
        for r in withbv:
            by_repo[r["repo"]].append(r)
        pooled = lambda samp: (lambda rs: sum(r["n_violated"] for r in rs) / max(1, sum(r["n_born_valid"] for r in rs)))([r for g in samp for r in g])
        anyf = lambda samp: (lambda rs: np.mean([r["n_violated"] > 0 for r in rs]))([r for g in samp for r in g])
        meanf = lambda samp: (lambda rs: np.mean([r["n_violated"] / r["n_born_valid"] for r in rs]))([r for g in samp for r in g])
        ks = sum(r["n_violated_strict"] for r in rows)
        ns = sum(r["n_born_valid_strict"] for r in rows)
        return {"files": len(rows), "files_with_constraints": len(withc), "files_with_born_valid": len(withbv),
                "constraints_at_head": sum(r["n_constraints"] for r in rows), "median_constraints_per_file": float(np.median([r["n_constraints"] for r in rows])) if rows else None,
                "born_valid_at_head": n, "violated_at_head": k, "pooled_drift": k / n if n else None,
                "pooled_drift_ci": cluster_boot(by_repo, pooled, rng).tolist() if n else None,
                "mean_file_drift": float(np.mean([r["n_violated"] / r["n_born_valid"] for r in withbv])) if withbv else None,
                "mean_file_drift_ci": cluster_boot(by_repo, meanf, rng).tolist() if withbv else None,
                "files_with_any_violation": any_v, "share_files_any_violation": any_v / len(withbv) if withbv else None,
                "share_files_any_violation_ci": cluster_boot(by_repo, anyf, rng).tolist() if withbv else None,
                "never_valid_at_head": sum(r["n_never_valid"] for r in rows),
                "share_never_valid": sum(r["n_never_valid"] for r in rows) / max(1, sum(r["n_constraints"] for r in rows)),
                "strict_born_valid": ns, "strict_violated": ks, "strict_pooled_drift": ks / ns if ns else None}

    S["head_drift"] = {"context": head_stats(ctx_files), "readme": head_stats([r for r in file_rows if not r["is_ctx"]])}
    for ft in ["AGENTS.md", "CLAUDE.md", ".cursorrules", "copilot-instructions.md"]:
        S["head_drift"][ft] = head_stats([r for r in ctx_files if r["ftype"] == ft])
    # by constraint kind at head (context files)
    S["head_by_kind"] = {}
    for is_ctx, label in ((1, "context"), (0, "readme")):
        S["head_by_kind"][label] = {}
        for kind in ["path", "script", "target", "manifest", "dep"]:
            cs = [c for c in cons_rows if c["is_ctx"] == is_ctx and c["kind"] == kind and c["live_head"]]
            bv = [c for c in cs if c["born_valid"]]
            k = sum(1 for c in bv if c["head_code"] == 0)
            S["head_by_kind"][label][kind] = {"at_head": len(cs), "born_valid": len(bv), "violated": k, "drift": k / len(bv) if bv else None,
                                             "wilson": wilson(k, len(bv)), "never_valid": sum(1 for c in cs if not c["ever_valid"])}

    # ---- RQ2 dynamics: survival, incidence, repair (repair is reported under RQ3)
    def dyn(is_ctx):
        cs = [c for c in cons_rows if c["is_ctx"] == is_ctx and c["born_valid"]]
        by_repo = collections.defaultdict(list)
        for c in cs:
            by_repo[c["repo"]].append(c)

        def km_stats(samp):
            rs = [c for g in samp for c in g]
            t, s = km([c["days_to_break_or_censor"] for c in rs], [c["broke"] for c in rs])
            return [km_at(t, s, 90), km_at(t, s, 180), km_at(t, s, 365)]

        def rate(samp):
            rs = [c for g in samp for c in g]
            return 36525.0 * sum(c["n_breaks"] for c in rs) / max(1e-9, sum(c["exposure_days"] for c in rs))

        t, s = km([c["days_to_break_or_censor"] for c in cs], [c["broke"] for c in cs])
        out = {"born_valid_lifetimes": len(cs), "repos": len(by_repo), "broke": sum(c["broke"] for c in cs),
               "share_broke": sum(c["broke"] for c in cs) / len(cs),
               "km_survival_90_180_365": km_stats(list(by_repo.values())), "km_ci": cluster_boot(by_repo, km_stats, rng).T.tolist(),
               "km_median_days": km_median(t, s), "max_followup_days": float(max(c["days_to_break_or_censor"] for c in cs)),
               "exposure_constraint_years": sum(c["exposure_days"] for c in cs) / 365.25, "breaks": sum(c["n_breaks"] for c in cs),
               "breaks_per_100_constraint_years": rate(list(by_repo.values())), "rate_ci": cluster_boot(by_repo, rate, rng).tolist()}
        # exponential half-life implied by the incidence rate (model-based, stated as such)
        lam = out["breaks_per_100_constraint_years"] / 100.0
        out["implied_half_life_years_constant_hazard"] = math.log(2) / lam if lam > 0 else None
        out["by_kind"] = {}
        for kind in ["path", "script", "target", "manifest", "dep"]:
            ks = [c for c in cs if c["kind"] == kind]
            ex = sum(c["exposure_days"] for c in ks) / 365.25
            out["by_kind"][kind] = {"lifetimes": len(ks), "breaks": sum(c["n_breaks"] for c in ks), "exposure_years": ex,
                                    "rate_per_100cy": 100 * sum(c["n_breaks"] for c in ks) / ex if ex else None}
        return out, by_repo

    S["dynamics"] = {}
    S["dynamics"]["context"], ctx_groups = dyn(1)
    S["dynamics"]["readme"], rd_groups = dyn(0)
    # rate ratio context / readme with paired cluster bootstrap over repositories
    repos_all = sorted(set(ctx_groups) | set(rd_groups))

    def rr(idx):
        num = den = e1 = e0 = 0.0
        for i in idx:
            r = repos_all[i]
            for c in ctx_groups.get(r, []):
                num += c["n_breaks"]; e1 += c["exposure_days"]
            for c in rd_groups.get(r, []):
                den += c["n_breaks"]; e0 += c["exposure_days"]
        return (num / e1) / (den / e0) if e1 and e0 and den else float("nan")

    boots = [rr(rng.integers(0, len(repos_all), len(repos_all))) for _ in range(B)]
    S["dynamics"]["rate_ratio_context_over_readme"] = {"estimate": rr(range(len(repos_all))), "ci": np.nanpercentile(boots, [2.5, 97.5]).tolist()}

    def repair(is_ctx):
        bs = [b for b in break_rows if b["is_ctx"] == is_ctx and b["born_valid"]]
        if not bs:
            return {}
        ends = collections.Counter(b["end"] for b in bs)
        t, s = km([b["days_broken"] for b in bs], [b["end"] != "open" for b in bs])
        closed = [b["days_broken"] for b in bs if b["end"] != "open"]
        open_ = [b["days_broken"] for b in bs if b["end"] == "open"]
        by_repo = collections.defaultdict(list)
        for b in bs:
            by_repo[b["repo"]].append(b)

        def st(samp):
            rs = [b for g in samp for b in g]
            tt, ss = km([b["days_broken"] for b in rs], [b["end"] != "open" for b in rs])
            return [np.mean([b["end"] == "open" for b in rs]), 1 - km_at(tt, ss, 7), 1 - km_at(tt, ss, 30), 1 - km_at(tt, ss, 90),
                    np.mean([b["ctx_touched_in_break_commit"] for b in rs])]

        return {"break_episodes": len(bs), "repos": len(by_repo), "exact_commit_located": sum(b["exact"] for b in bs), "ends": dict(ends),
                "share_open_at_head": ends["open"] / len(bs), "km_median_days_to_repair": km_median(t, s),
                "repaired_within_7_30_90_days": [1 - km_at(t, s, 7), 1 - km_at(t, s, 30), 1 - km_at(t, s, 90)],
                "boot_ci_open_7_30_90_touched": cluster_boot(by_repo, st, rng).T.tolist(),
                "median_days_broken_closed": float(np.median(closed)) if closed else None,
                "median_days_open_so_far": float(np.median(open_)) if open_ else None,
                "iqr_days_open_so_far": [float(x) for x in np.percentile(open_, [25, 75])] if open_ else None,
                "file_touched_in_break_commit": sum(b["ctx_touched_in_break_commit"] for b in bs),
                "share_file_touched_in_break_commit": float(np.mean([b["ctx_touched_in_break_commit"] for b in bs]))}

    S["repair"] = {"context": repair(1), "readme": repair(0)}

    # ---- RQ3 co-change: when a commit invalidates a referenced target, is the file updated in that commit
    def coupling(is_ctx):
        sync = [r for r in sync_rows if r["is_ctx"] == is_ctx and r["type"] == "sync_removal" and r["born_valid"]]
        brk = [b for b in break_rows if b["is_ctx"] == is_ctx and b["born_valid"]]
        by_repo = collections.defaultdict(lambda: [0, 0])
        for r in sync:
            by_repo[r["repo"]][0] += 1
        for b in brk:
            by_repo[b["repo"]][1] += 1
        f = lambda samp: sum(g[0] for g in samp) / max(1, sum(g[0] + g[1] for g in samp))
        rem = collections.Counter(r["type"] for r in sync_rows if r["is_ctx"] == is_ctx)
        return {"in_sync_updates": len(sync), "breaks": len(brk), "invalidations": len(sync) + len(brk),
                "in_sync_share": len(sync) / max(1, len(sync) + len(brk)), "ci": cluster_boot(by_repo, f, rng).tolist(),
                "repos": len(by_repo), "removals_by_type": dict(rem)}

    S["coupling"] = {"context": coupling(1), "readme": coupling(0)}
    # maintenance activity
    S["maintenance"] = {
        "ctx_commit_share_of_window": float(np.mean([min(1.0, sum(fr["n_versions"] for fr in ctx_files if fr["repo"] == r["repo"]) / max(1, r["window_commits"])) for r in repo_rows])),
    }

    # ---- extra: repository-level prevalence, ever-broken files, paired differences, who breaks
    def repo_any(is_ctx):
        by = collections.defaultdict(lambda: [0, 0])
        for r in file_rows:
            if r["is_ctx"] == is_ctx and r["n_born_valid"] > 0:
                by[r["repo"]][0] += r["n_violated"]
                by[r["repo"]][1] += r["n_born_valid"]
        k = sum(1 for v in by.values() if v[0] > 0)
        return {"repos": len(by), "repos_any_violation": k, "share": k / len(by), "wilson": wilson(k, len(by))}

    S["repo_level"] = {"context": repo_any(1), "readme": repo_any(0)}
    ever = collections.defaultdict(set)
    for b in break_rows:
        if b["born_valid"]:
            ever[b["is_ctx"]].add((b["repo"], b["file"]))
    files_bv = {1: {(c["repo"], c["file"]) for c in cons_rows if c["is_ctx"] and c["born_valid"]},
                0: {(c["repo"], c["file"]) for c in cons_rows if not c["is_ctx"] and c["born_valid"]}}
    S["ever_broken"] = {lab: {"files_with_anchored": len(files_bv[k]), "files_ever_broken": len(ever[k]),
                              "share": len(ever[k]) / len(files_bv[k]), "wilson": wilson(len(ever[k]), len(files_bv[k])),
                              "repos_ever_broken": len({r for r, _ in ever[k]})} for k, lab in ((1, "context"), (0, "readme"))}
    # concentration of breaks
    per_repo_breaks = collections.Counter(b["repo"] for b in break_rows if b["is_ctx"] and b["born_valid"])
    tot = sum(per_repo_breaks.values())
    top = sorted(per_repo_breaks.values(), reverse=True)
    S["concentration"] = {"repos_with_breaks": len(per_repo_breaks), "top10_repos_share_of_breaks": sum(top[:10]) / tot if tot else None,
                          "max_breaks_one_repo": top[0] if top else 0}
    # paired cluster bootstrap of context minus README differences
    def paired(fn):
        repos_all = sorted({r["repo"] for r in repo_rows})
        est = fn(set(repos_all), None)
        bs = []
        for _ in range(B):
            idx = rng.integers(0, len(repos_all), len(repos_all))
            w = collections.Counter(repos_all[i] for i in idx)
            bs.append(fn(None, w))
        return {"diff": est, "ci": np.nanpercentile(np.array(bs, float), [2.5, 97.5]).tolist()}

    def w_of(repo, keep, w):
        return (1 if repo in keep else 0) if w is None else w.get(repo, 0)

    def d_insync(keep, w):
        out = []
        for is_ctx in (1, 0):
            sy = sum(w_of(r["repo"], keep, w) for r in sync_rows if r["is_ctx"] == is_ctx and r["type"] == "sync_removal" and r["born_valid"])
            br = sum(w_of(b["repo"], keep, w) for b in break_rows if b["is_ctx"] == is_ctx and b["born_valid"])
            out.append(sy / (sy + br) if sy + br else float("nan"))
        return out[0] - out[1]

    def d_open(keep, w):
        out = []
        for is_ctx in (1, 0):
            bs_ = [(w_of(b["repo"], keep, w), b["end"] == "open") for b in break_rows if b["is_ctx"] == is_ctx and b["born_valid"]]
            den = sum(x for x, _ in bs_)
            out.append(sum(x for x, o in bs_ if o) / den if den else float("nan"))
        return out[0] - out[1]

    def d_drift(keep, w):
        out = []
        for is_ctx in (1, 0):
            k = sum(w_of(r["repo"], keep, w) * r["n_violated"] for r in file_rows if r["is_ctx"] == is_ctx)
            n = sum(w_of(r["repo"], keep, w) * r["n_born_valid"] for r in file_rows if r["is_ctx"] == is_ctx)
            out.append(k / n if n else float("nan"))
        return out[0] - out[1]

    S["paired_diff_context_minus_readme"] = {"in_sync_share": paired(d_insync), "share_open": paired(d_open), "pooled_drift": paired(d_drift)}
    # who breaks: agent-attributed share among breaking commits versus all commits of the same repositories
    bc = {(b["repo"], b["commit"]): b["agent_commit"] for b in break_rows if b["is_ctx"] and b["born_valid"] and b["commit"] and b["agent_commit"] != ""}
    brepos = {r for r, _ in bc}
    base_n = sum(r["window_commits_all"] for r in repo_rows if r["repo"] in brepos)
    base_k = sum(r["window_agent_commits"] for r in repo_rows if r["repo"] in brepos)
    S["who_breaks"] = {"breaking_commits": len(bc), "agent_attributed": sum(bc.values()), "share": sum(bc.values()) / max(1, len(bc)),
                       "wilson": wilson(sum(bc.values()), len(bc)), "base_commits": base_n, "base_agent": base_k,
                       "base_share": base_k / max(1, base_n),
                       "all_repos_agent_share": sum(r["window_agent_commits"] for r in repo_rows) / max(1, sum(r["window_commits_all"] for r in repo_rows))}

    # ---- baselines run on the same data (context files, HEAD)
    live = [c for c in cons_rows if c["is_ctx"] and c["live_head"]]
    naive_viol = [c for c in live if c["head_code"] == 0]
    anchored_viol = [c for c in naive_viol if c["born_valid"]]
    two_snap = [c for c in anchored_viol if c["in_first_version"]]
    all_breaks = [b for b in break_rows if b["is_ctx"] and b["born_valid"]]
    S["baselines"] = {
        "single_snapshot_flagged": len(naive_viol), "single_snapshot_rate": len(naive_viol) / len(live),
        "single_snapshot_files_flagged": len({(c["repo"], c["file"]) for c in naive_viol}),
        "single_snapshot_share_files": len({(c["repo"], c["file"]) for c in naive_viol}) / len({(c["repo"], c["file"]) for c in live}),
        "anchored_flagged": len(anchored_viol), "share_of_single_snapshot_flags_that_are_anchored": len(anchored_viol) / max(1, len(naive_viol)),
        "two_snapshot_flagged": len(two_snap), "two_snapshot_recall_of_anchored_head": len(two_snap) / max(1, len(anchored_viol)),
        "break_episodes_full_history": len(all_breaks), "break_episodes_visible_at_head": sum(1 for b in all_breaks if b["end"] == "open"),
        "share_breaks_invisible_at_head": sum(1 for b in all_breaks if b["end"] != "open") / max(1, len(all_breaks)),
        "born_invalid_later_valid_at_head": sum(1 for c in live if not c["born_valid"] and c["head_code"] != 0),
    }

    # ---- checker check for the consistency analysis (exploratory, not in the paper): raw occurrences of "<tool> or <tool>" in head texts
    OR_RX = re.compile(r"\b(npm|yarn|pnpm|bun|pip|poetry|uv|jest|vitest|pytest|eslint|biome|prettier|ruff|black)`?\s+or\s+`?(npm|yarn|pnpm|bun|pip|poetry|uv|jest|vitest|pytest|eslint|biome|prettier|ruff|black)\b", re.I)
    NEG_NEAR = re.compile(r"(never|not|n't|avoid|\bno\b)[^.\n]{0,40}$", re.I)
    raw_or = raw_or_neg = 0
    for d in load():
        for p, fd in d.get("files", {}).items():
            if p == "README.md":
                continue
            for m in OR_RX.finditer(fd["head_text"]):
                raw_or += 1
                raw_or_neg += bool(NEG_NEAR.search(fd["head_text"][max(0, m.start() - 60):m.start()]))

    # ---- consistency of command mentions (exploratory, not in the paper)
    nr = sum(r["n_rules"] for r in rule_rows)
    nchoice = sum(r["choice"] for r in rule_rows)
    files_rules = [r for r in rule_rows if r["n_rules"] > 0]
    by_repo = collections.defaultdict(list)
    for r in files_rules:
        by_repo[r["repo"]].append(r)
    S["consistency"] = {
        "files_analysed": len(rule_rows), "files_with_rules": len(files_rules), "rules": nr,
        "forms": {k: sum(r[k] for r in rule_rows) for k in ["unit_pos", "unit_neg", "horn_definite", "horn_negative", "choice"]},
        "unit_pos_from_command_mentions": sum(r["unit_pos_cmd"] for r in rule_rows), "axioms": sum(r["n_axioms"] for r in rule_rows),
        "horn_rules": nr - nchoice, "horn_share": (nr - nchoice) / nr if nr else None, "horn_share_wilson": wilson(nr - nchoice, nr),
        "horn_share_ci_cluster": cluster_boot(by_repo, lambda samp: (lambda rs: 1 - sum(r["choice"] for r in rs) / max(1, sum(r["n_rules"] for r in rs)))([r for g in samp for r in g]), rng).tolist() if files_rules else None,
        "files_all_horn": sum(r["all_horn"] for r in files_rules), "share_files_all_horn": float(np.mean([r["all_horn"] for r in files_rules])) if files_rules else None,
        "median_rules_per_file": float(np.median([r["n_rules"] for r in files_rules])) if files_rules else None,
        "max_rules_per_file": max([r["n_rules"] for r in files_rules]) if files_rules else None,
        "files_unsat": sum(1 for r in files_rules if not r["satisfiable"]),
        "share_files_unsat": float(np.mean([not r["satisfiable"] for r in files_rules])) if files_rules else None,
        "share_files_unsat_wilson": wilson(sum(1 for r in files_rules if not r["satisfiable"]), len(files_rules)),
        "cores": len({(r["repo"], r["file"], r["core"]) for r in core_rows}),
        "raw_or_pairs": raw_or, "raw_or_pairs_in_prohibitions": raw_or_neg,
        "core_sizes": dict(collections.Counter(r["core_size"] for r in core_rows if True).items()),
    }

    # ---- compliance with commit-message convention (descriptive, exploratory, not in the paper)
    def cc_summary(rows, minn=20):
        rows = [r for r in rows if r["n_pre"] >= minn and r["n_post"] >= minn]
        if not rows:
            return {"repos": 0}
        pre = np.array([r["cc_pre"] / r["n_pre"] for r in rows])
        post = np.array([r["cc_post"] / r["n_post"] for r in rows])
        diff = post - pre
        bs = [np.mean(diff[rng.integers(0, len(diff), len(diff))]) for _ in range(B)]
        from scipy import stats
        w = stats.wilcoxon(diff) if np.any(diff != 0) else None
        return {"repos": len(rows), "mean_pre": float(pre.mean()), "mean_post": float(post.mean()), "median_pre": float(np.median(pre)),
                "median_post": float(np.median(post)), "mean_diff": float(diff.mean()), "diff_ci": np.percentile(bs, [2.5, 97.5]).tolist(),
                "wilcoxon_p": float(w.pvalue) if w else None, "share_post_below_half": float(np.mean(post < 0.5)),
                "share_post_above_90": float(np.mean(post >= 0.9))}

    # one row per repository: prefer the file that states the rule
    best = {}
    for r in cc_rows:
        if r["repo"] not in best or (r["has_rule"] and not best[r["repo"]]["has_rule"]):
            best[r["repo"]] = r
    with_rule = [r for r in best.values() if r["has_rule"]]
    no_rule = [r for r in best.values() if not r["has_rule"]]
    post_only = [r for r in with_rule if r["n_post"] >= 20]
    ag = [r for r in with_rule if r["n_post_agent"] >= 10 and r["n_post_other"] >= 10]
    S["compliance"] = {
        "repos_with_rule": len(with_rule), "repos_without_rule": len(no_rule),
        "with_rule_pre_post": cc_summary(with_rule), "without_rule_pre_post": cc_summary(no_rule),
        "with_rule_post_only": {"repos": len(post_only), "mean_compliance": float(np.mean([r["cc_post"] / r["n_post"] for r in post_only])) if post_only else None,
                                "median_compliance": float(np.median([r["cc_post"] / r["n_post"] for r in post_only])) if post_only else None,
                                "pooled_share": sum(r["cc_post"] for r in post_only) / max(1, sum(r["n_post"] for r in post_only)),
                                "pooled_commits": sum(r["n_post"] for r in post_only), "pooled_cc": sum(r["cc_post"] for r in post_only),
                                "share_repos_below_half": float(np.mean([r["cc_post"] / r["n_post"] < 0.5 for r in post_only])) if post_only else None,
                                "share_repos_at_least_90": float(np.mean([r["cc_post"] / r["n_post"] >= 0.9 for r in post_only])) if post_only else None},
        "agent_vs_other_after_rule": {"repos": len(ag),
                                      "mean_agent": float(np.mean([r["cc_post_agent"] / r["n_post_agent"] for r in ag])) if ag else None,
                                      "mean_other": float(np.mean([r["cc_post_other"] / r["n_post_other"] for r in ag])) if ag else None,
                                      "pooled_agent": [sum(r["cc_post_agent"] for r in ag), sum(r["n_post_agent"] for r in ag)],
                                      "pooled_other": [sum(r["cc_post_other"] for r in ag), sum(r["n_post_other"] for r in ag)]},
    }
    wr = [r for r in with_rule if r["n_pre"] >= 20 and r["n_post"] >= 20]
    nrr = [r for r in no_rule if r["n_pre"] >= 20 and r["n_post"] >= 20]
    dw = np.array([r["cc_post"] / r["n_post"] - r["cc_pre"] / r["n_pre"] for r in wr])
    dn = np.array([r["cc_post"] / r["n_post"] - r["cc_pre"] / r["n_pre"] for r in nrr])
    if len(dw) and len(dn):
        bs = [dw[rng.integers(0, len(dw), len(dw))].mean() - dn[rng.integers(0, len(dn), len(dn))].mean() for _ in range(B)]
        S["compliance"]["gain_difference_rule_minus_no_rule"] = {"estimate": float(dw.mean() - dn.mean()), "ci": np.percentile(bs, [2.5, 97.5]).tolist()}
    S["compliance"]["rule_at_creation_share"] = float(np.mean([r["rule_at_creation"] == 1 for r in with_rule])) if with_rule else None
    if len(ag) >= 6:
        from scipy import stats
        dd = np.array([r["cc_post_agent"] / r["n_post_agent"] - r["cc_post_other"] / r["n_post_other"] for r in ag])
        S["compliance"]["agent_vs_other_after_rule"]["mean_diff"] = float(dd.mean())
        S["compliance"]["agent_vs_other_after_rule"]["diff_ci"] = np.percentile([np.mean(dd[rng.integers(0, len(dd), len(dd))]) for _ in range(B)], [2.5, 97.5]).tolist()
        S["compliance"]["agent_vs_other_after_rule"]["wilcoxon_p"] = float(stats.wilcoxon(dd).pvalue) if np.any(dd != 0) else None

    json.dump(S, open(os.path.join(RES, "summary.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(S, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()

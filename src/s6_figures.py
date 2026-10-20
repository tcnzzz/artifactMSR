#!/usr/bin/env python3
"""Stage 6: figures for the manuscript, built only from artifact/results and the mined cache."""
import csv, gzip, json, os, sys, collections, datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s4_analyze import km, km_at

CACHE = os.environ.get("S03_CACHE") or os.path.expanduser("~/.cache/context-rot-study/S03")
if not os.path.isdir(os.path.join(CACHE, "mined")):  # fall back to the copy shipped inside the package
    CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ART, "results")
FIG = os.path.join(os.path.dirname(ART), "manuscript", "figures")
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "font.family": "DejaVu Sans"})
C_CTX, C_RD, C_OK, C_BAD = "#1f6fb4", "#888888", "#7fbf7b", "#d7301f"
SEED = 20261003


def rows(name):
    return list(csv.DictReader(open(os.path.join(RES, name))))


def kind_label(c):
    if c["kind"] == "path":
        t = c["target"]
        return "path, directory" if t.endswith("/") else ("path, bare file name" if "/" not in t else "path, file")
    return {"script": "package script", "target": "build target", "manifest": "tool manifest", "dep": "tool dependency"}[c["kind"]]


def fig_overview():
    """Worked example from one sampled repository: status timeline of compiled constraints (labels anonymised by kind)."""
    files = rows("files.csv")
    brk = rows("breaks.csv")
    per = collections.Counter((b["repo"], b["file"]) for b in brk if b["is_ctx"] == "1" and b["born_valid"] == "1")
    cand = [(f, per[(f["repo"], f["file"])]) for f in files if f["is_ctx"] == "1" and 8 <= int(f["n_constraints"]) <= 40
            and int(f["n_versions"]) >= 4 and per[(f["repo"], f["file"])] >= 2 and float(f["age_days"]) >= 120]
    cand.sort(key=lambda x: (-x[1], x[0]["repo"]))
    f = cand[0][0]
    d = json.load(gzip.open(os.path.join(CACHE, "mined", f["repo"].replace("/", "__") + ".json.gz"), "rt"))
    fd = d["files"][f["file"]]
    snap_ts = {s: ts for s, ts, _ in d["snaps"]}
    head = d["snaps"][-1][0]
    cons = sorted(fd["constraints"].items(), key=lambda kv: (kv[1]["obs"][0][0], kv[1]["line"]))
    anch = [kv for kv in cons if kv[1]["obs"][0][1] > 0]
    broke = [kv for kv in anch if any(c == 0 for _, c in kv[1]["obs"])]
    stable = [kv for kv in anch if all(c > 0 for _, c in kv[1]["obs"]) and kv[1]["obs"][-1][0] == head]
    removed = [kv for kv in anch if all(c > 0 for _, c in kv[1]["obs"]) and kv[1]["obs"][-1][0] != head]
    show = broke + stable[:3] + removed[:2]
    fig, ax = plt.subplots(figsize=(7.0, 0.2 * len(show) + 0.9))
    todate = lambda ts: datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
    for y, (key, c) in enumerate(reversed(show)):
        obs = c["obs"]
        for (a, ca), (b, cb) in zip(obs, obs[1:]):
            ax.plot([todate(snap_ts[a]), todate(snap_ts[b])], [y, y], color=C_OK if ca > 0 else C_BAD, lw=4.5, solid_capstyle="butt")
        if obs[-1][0] != head:
            ax.plot([todate(snap_ts[obs[-1][0]])], [y], marker="x", color="k", ms=4.5)
        ax.text(-0.01, y, f"{len(show) - y}. {kind_label(c)}", transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=6.5)
    for v, ts in fd["versions"]:
        ax.axvline(todate(ts), color="#bbbbbb", lw=0.5, zorder=0)
    ax.set_yticks([])
    ax.set_ylim(-0.7, len(show) - 0.3)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="x", labelsize=7)
    ax.legend(handles=[Patch(color=C_OK, label="constraint satisfied"), Patch(color=C_BAD, label="constraint violated"),
                       plt.Line2D([], [], color="k", marker="x", ls="", label="instruction removed from file"),
                       plt.Line2D([], [], color="#bbbbbb", lw=0.8, label="context file edited")],
              loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=4, frameon=False, fontsize=6.5)
    fig.subplots_adjust(left=0.2, right=0.99, top=0.98, bottom=0.27)
    fig.savefig(os.path.join(FIG, "overview.pdf"))
    plt.close(fig)
    # narrative facts, generated from the data
    ev = [e for e in d["events"] if e["file"] == f["file"] and e["type"] == "break"]
    bykey = {k: c for k, c in fd["constraints"].items()}
    ev = [e for e in ev if bykey[e["key"]]["obs"][0][1] > 0]
    days = collections.Counter(datetime.datetime.fromtimestamp(e["ts"], datetime.timezone.utc).strftime("%Y-%m-%d") for e in ev)
    birth = fd["versions"][0][1]
    first = min(ev, key=lambda e: e["ts"])
    open_head = sum(1 for k, c in broke if c["obs"][-1][0] == head and c["obs"][-1][1] == 0)
    # days each break stayed in the file
    stay = []
    for k, c in broke:
        o = c["obs"]
        t_break = next(e["ts"] for e in ev if e["key"] == k)
        nxt = [s for s, _, _ in d["snaps"] if s > o[-1][0]]
        t_end = snap_ts[nxt[0]] if nxt else snap_ts[head]
        stay.append((t_end - t_break) / 86400.0)
    info = {"repo": f["repo"], "file_type": f["ftype"], "n_constraints_head": int(f["n_constraints"]), "n_versions": int(f["n_versions"]),
            "age_days": float(f["age_days"]), "rows_shown": len(show), "rows_broken": len(broke), "rows_stable": len(stable[:3]), "rows_removed_valid": len(removed[:2]),
            "break_episodes": len(ev), "breaks_by_day": dict(sorted(days.items())), "largest_break_day": max(days.values()),
            "first_break_days_after_creation": round((first["ts"] - birth) / 86400.0), "open_at_head": open_head,
            "ctx_touched_in_any_break_commit": int(any(e["ctx_touched"] for e in ev)),
            "min_days_in_file_after_break": round(min(stay)), "max_days_in_file_after_break": round(max(stay)),
            "shown": [{"kind": c["kind"], "target": c["target"], "line": c["line"]} for _, c in show]}
    json.dump(info, open(os.path.join(RES, "overview_example.json"), "w"), indent=1)


def fig_head():
    S = json.load(open(os.path.join(RES, "summary.json")))
    R = json.load(open(os.path.join(RES, "robustness.json")))
    fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.9))
    ax = axs[0]
    types = ["AGENTS.md", "CLAUDE.md", ".cursorrules", "copilot-instructions.md", "readme"]
    names = ["AGENTS", "CLAUDE", "cursor", "copilot", "README"]
    vals = [100 * (S["head_drift"][t]["pooled_drift"] or 0) for t in types]
    cis = [[100 * x for x in (S["head_drift"][t]["pooled_drift_ci"] or [0, 0])] for t in types]
    ax.bar(range(5), vals, color=[C_CTX] * 4 + [C_RD], yerr=[[max(0, v - c[0]) for v, c in zip(vals, cis)], [max(0, c[1] - v) for v, c in zip(vals, cis)]],
           error_kw={"lw": 0.7}, capsize=1.5)
    ax.set_xticks(range(5))
    ax.set_xticklabels(names, fontsize=5.5, rotation=35, ha="right")
    ax.set_ylabel("drift at head (%)", fontsize=7)
    ax.tick_params(axis="y", labelsize=6)
    ax = axs[1]
    groups = [("slashed_paths", "path with /"), ("bare_names", "bare name"), ("non_path", "command")]
    for j, (lab, col) in enumerate((("context", C_CTX), ("readme", C_RD))):
        v = [100 * R["drift_sens"][lab][g]["drift"] for g, _ in groups]
        w = [[100 * x for x in R["drift_sens"][lab][g]["wilson"]] for g, _ in groups]
        ax.bar(np.arange(3) + (j - 0.5) * 0.4, v, 0.4, color=col, yerr=[[max(0, a - b[0]) for a, b in zip(v, w)], [max(0, b[1] - a) for a, b in zip(v, w)]],
               error_kw={"lw": 0.7}, capsize=1.5, label="context files" if lab == "context" else "README")
    ax.set_xticks(range(3))
    ax.set_xticklabels([g for _, g in groups], fontsize=5.5, rotation=35, ha="right")
    ax.tick_params(axis="y", labelsize=6)
    ax.legend(frameon=False, fontsize=5.5)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(FIG, "head_drift.pdf"))
    plt.close(fig)


def fig_dynamics():
    brk = rows("breaks.csv")
    R = json.load(open(os.path.join(RES, "robustness.json")))
    fig, axs = plt.subplots(1, 4, figsize=(7.1, 1.85))
    g = R["cif_curves"]["grid"]
    for ax, key, title in ((axs[0], "context", "context files"), (axs[1], "readme_entry_observed", "README (entry observed)")):
        c = R["cif_curves"][key]
        b, s_, v = np.array(c["break"]) * 100, np.array(c["sync_removal"]) * 100, np.array(c["removal_valid"]) * 100
        ax.stackplot(g, b, s_, v, colors=[C_BAD, "#fdae61", "#cccccc"], labels=["left in file (break)", "updated in sync", "removed while valid"], lw=0)
        ax.set_ylim(0, 65)
        ax.set_xlim(0, 365)
        ax.set_title(title, fontsize=7, pad=2)
        ax.set_xlabel("days since entry", fontsize=7)
    axs[0].set_ylabel("cumulative incidence (%)", fontsize=7)
    axs[0].legend(frameon=False, fontsize=5.5, loc="upper left")
    ax = axs[2]
    a = R["age"]["all_files"]
    ax.plot([x["age"] for x in a], [100 * x["mean_drift"] for x in a], color=C_CTX, marker="o", ms=2.5, label="all files (population varies)")
    ax.fill_between([x["age"] for x in a], [100 * x["ci"][0] for x in a], [100 * x["ci"][1] for x in a], color=C_CTX, alpha=0.2, lw=0)
    c = R["age"]["cohort_240"]
    ax.plot([x["age"] for x in c], [100 * x["mean_drift"] for x in c], color="k", ls="--", lw=0.8, label="cohort aged 240+ days")
    ax.set_xlabel("age of context file (days)", fontsize=7)
    ax.set_ylabel("mean drift (%)", fontsize=7)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=5.5, loc="upper left")
    ax = axs[3]
    grid = np.linspace(0, 365, 74)
    for is_ctx, col, lab in (("1", C_CTX, "context files"), ("0", C_RD, "README")):
        bsr = [b for b in brk if b["is_ctx"] == is_ctx and b["born_valid"] == "1"]
        t, s = km([float(b["days_broken"]) for b in bsr], [b["end"] != "open" for b in bsr])
        ax.step(grid, [100 * km_at(t, s, x) for x in grid], color=col, where="post", label=f"{lab} (n={len(bsr)})")
    ax.set_xlabel("days since break", fontsize=7)
    ax.set_ylabel("breaks unrepaired (%)", fontsize=7)
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=5.5)
    for ax in axs:
        ax.tick_params(labelsize=6)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(FIG, "dynamics.pdf"))
    plt.close(fig)


def fig_compliance():
    cc = rows("commit_convention.csv")
    best = {}
    for r in cc:
        if r["repo"] not in best or (r["has_rule"] == "1" and best[r["repo"]]["has_rule"] != "1"):
            best[r["repo"]] = r
    fig, ax = plt.subplots(figsize=(3.3, 2.3))
    for has, col, lab, mk in (("0", C_RD, "no stated rule", "o"), ("1", C_BAD, "rule stated in context file", "^")):
        rs = [r for r in best.values() if r["has_rule"] == has and int(r["n_pre"]) >= 20 and int(r["n_post"]) >= 20]
        ax.scatter([int(r["cc_pre"]) / int(r["n_pre"]) for r in rs], [int(r["cc_post"]) / int(r["n_post"]) for r in rs], s=9, color=col,
                   marker=mk, alpha=0.7, label=f"{lab} (n={len(rs)})", lw=0)
    ax.plot([0, 1], [0, 1], color="k", lw=0.5, ls=":")
    ax.set_xlabel("share of conforming commits before")
    ax.set_ylabel("share of conforming commits after")
    ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    fig.tight_layout(pad=0.4)
    fig.savefig(os.path.join(FIG, "compliance.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_overview()
    fig_head()
    fig_dynamics()
    print("figures written to", FIG)

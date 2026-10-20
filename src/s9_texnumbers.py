#!/usr/bin/env python3
"""Stage 9: emit manuscript/numbers.tex, one LaTeX macro per number quoted in the paper,
and artifact/claims.md, which maps each macro to its results file and key."""
import csv, json, os

ART = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ART, "results")
OUT = os.path.join(os.path.dirname(ART), "manuscript", "numbers.tex")
S = json.load(open(os.path.join(RES, "summary.json")))
V = json.load(open(os.path.join(RES, "validation_summary.json")))
L = json.load(open(os.path.join(RES, "llm_second_rater_summary.json"))) if os.path.exists(os.path.join(RES, "llm_second_rater_summary.json")) else None
AGE = list(csv.DictReader(open(os.path.join(RES, "drift_by_age_summary.csv"))))
REPOS = list(csv.DictReader(open(os.path.join(RES, "repos.csv"))))
OV = json.load(open(os.path.join(RES, "overview_example.json")))

M = []  # (macro, value, source file, key path)


def add(name, value, src, key):
    M.append((name, str(value), src, key))


def pct(x, d=1):
    return f"{100 * x:.{d}f}"


def num(x):
    return f"{int(x):,}".replace(",", "{,}")


def ci(pair, d=1, scale=100):
    return f"{scale * pair[0]:.{d}f} to {scale * pair[1]:.{d}f}"


s = "summary.json"
F, C = S["funnel"], S["corpus"]
add("NHits", num(F["search_hits"]), s, "funnel.search_hits")
add("NRootRepos", num(F["repos_with_root_file"]), s, "funnel.repos_with_root_file")
add("NRepos", num(C["repos"]), s, "corpus.repos")
add("NCtxFiles", num(C["context_files"]), s, "corpus.context_files")
add("NReadme", num(C["readme_files"]), s, "corpus.readme_files")
for k, n in (("AGENTS.md", "Agents"), ("CLAUDE.md", "Claude"), (".cursorrules", "Cursor"), ("copilot-instructions.md", "Copilot")):
    add("NFiles" + n, num(C["files_by_type"][k]), s, f"corpus.files_by_type.{k}")
    h = S["head_drift"][k]
    add("Drift" + n, pct(h["pooled_drift"], 2), s, f"head_drift.{k}.pooled_drift")
    add("DriftCI" + n, ci(h["pooled_drift_ci"], 2), s, f"head_drift.{k}.pooled_drift_ci")
    add("AnyViol" + n, pct(h["share_files_any_violation"]), s, f"head_drift.{k}.share_files_any_violation")
    add("Anch" + n, num(h["born_valid_at_head"]), s, f"head_drift.{k}.born_valid_at_head")
    add("Viol" + n, num(h["violated_at_head"]), s, f"head_drift.{k}.violated_at_head")
    add("MedCons" + n, f"{h['median_constraints_per_file']:.0f}", s, f"head_drift.{k}.median_constraints_per_file")
add("MedStars", f"{C['median_stars']:.0f}", s, "corpus.median_stars")
add("StarsIQR", f"{C['stars_iqr'][0]:.0f} to {C['stars_iqr'][1]:.0f}", s, "corpus.stars_iqr")
add("MedAge", f"{C['median_age_days']:.0f}", s, "corpus.median_age_days")
add("AgeIQR", f"{C['age_iqr'][0]:.0f} to {C['age_iqr'][1]:.0f}", s, "corpus.age_iqr")
add("MedVersions", f"{C['median_versions']:.0f}", s, "corpus.median_versions")
add("ShareSingleVersion", pct(C["share_single_version"]), s, "corpus.share_single_version")
add("MedSinceEdit", f"{C['median_days_since_edit']:.0f}", s, "corpus.median_days_since_edit")
add("NSnapshots", num(C["total_snapshots"]), s, "corpus.total_snapshots")
add("NFullEnum", num(C["fully_enumerated_repos"]), s, "corpus.fully_enumerated_repos")
add("NLifeCtx", num(C["constraint_lifetimes_ctx"]), s, "corpus.constraint_lifetimes_ctx")
add("NLifeReadme", num(C["constraint_lifetimes_readme"]), s, "corpus.constraint_lifetimes_readme")
add("LangTop", ", ".join(f"{a} ({b})" for a, b in C["languages_top"][:5]), s, "corpus.languages_top")
add("NWindowCommits", num(sum(int(r["window_commits"]) for r in REPOS)), "repos.csv", "sum of window_commits")
add("CtxCommitShare", pct(S["maintenance"]["ctx_commit_share_of_window"]), s, "maintenance.ctx_commit_share_of_window")

for lab, n in (("context", "Ctx"), ("readme", "Rd")):
    h = S["head_drift"][lab]
    add("ConsHead" + n, num(h["constraints_at_head"]), s, f"head_drift.{lab}.constraints_at_head")
    add("MedCons" + n, f"{h['median_constraints_per_file']:.0f}", s, f"head_drift.{lab}.median_constraints_per_file")
    add("FilesWithCons" + n, num(h["files_with_constraints"]), s, f"head_drift.{lab}.files_with_constraints")
    add("FilesAnch" + n, num(h["files_with_born_valid"]), s, f"head_drift.{lab}.files_with_born_valid")
    add("Anch" + n, num(h["born_valid_at_head"]), s, f"head_drift.{lab}.born_valid_at_head")
    add("Viol" + n, num(h["violated_at_head"]), s, f"head_drift.{lab}.violated_at_head")
    add("Drift" + n, pct(h["pooled_drift"], 2), s, f"head_drift.{lab}.pooled_drift")
    add("DriftCI" + n, ci(h["pooled_drift_ci"], 2), s, f"head_drift.{lab}.pooled_drift_ci")
    add("AnyViol" + n, pct(h["share_files_any_violation"]), s, f"head_drift.{lab}.share_files_any_violation")
    add("AnyViolCI" + n, ci(h["share_files_any_violation_ci"]), s, f"head_drift.{lab}.share_files_any_violation_ci")
    add("FilesAnyViol" + n, num(h["files_with_any_violation"]), s, f"head_drift.{lab}.files_with_any_violation")
    add("NeverValid" + n, num(h["never_valid_at_head"]), s, f"head_drift.{lab}.never_valid_at_head")
    add("ShareNever" + n, pct(h["share_never_valid"]), s, f"head_drift.{lab}.share_never_valid")
    add("StrictDrift" + n, pct(h["strict_pooled_drift"], 2), s, f"head_drift.{lab}.strict_pooled_drift")
    add("StrictViol" + n, num(h["strict_violated"]), s, f"head_drift.{lab}.strict_violated")
    add("StrictAnch" + n, num(h["strict_born_valid"]), s, f"head_drift.{lab}.strict_born_valid")
    r = S["repo_level"][lab]
    add("RepoAny" + n, pct(r["share"]), s, f"repo_level.{lab}.share")
    add("RepoAnyCI" + n, ci(r["wilson"]), s, f"repo_level.{lab}.wilson")
    add("RepoAnyK" + n, num(r["repos_any_violation"]), s, f"repo_level.{lab}.repos_any_violation")
    add("RepoAnyN" + n, num(r["repos"]), s, f"repo_level.{lab}.repos")
    e = S["ever_broken"][lab]
    add("EverBroken" + n, pct(e["share"]), s, f"ever_broken.{lab}.share")
    add("EverBrokenCI" + n, ci(e["wilson"]), s, f"ever_broken.{lab}.wilson")
    add("EverBrokenK" + n, num(e["files_ever_broken"]), s, f"ever_broken.{lab}.files_ever_broken")
    add("EverBrokenN" + n, num(e["files_with_anchored"]), s, f"ever_broken.{lab}.files_with_anchored")
    d = S["dynamics"][lab]
    add("Life" + n, num(d["born_valid_lifetimes"]), s, f"dynamics.{lab}.born_valid_lifetimes")
    add("Breaks" + n, num(d["breaks"]), s, f"dynamics.{lab}.breaks")
    add("Exposure" + n, num(round(d["exposure_constraint_years"])), s, f"dynamics.{lab}.exposure_constraint_years")
    add("Rate" + n, f"{d['breaks_per_100_constraint_years']:.1f}", s, f"dynamics.{lab}.breaks_per_100_constraint_years")
    add("RateCI" + n, ci(d["rate_ci"], 1, 1), s, f"dynamics.{lab}.rate_ci")
    add("HalfLife" + n, f"{d['implied_half_life_years_constant_hazard']:.1f}", s, f"dynamics.{lab}.implied_half_life_years_constant_hazard")
    for i, t in enumerate(("Ninety", "HalfYear", "Year")):
        add("Surv" + t + n, pct(d["km_survival_90_180_365"][i]), s, f"dynamics.{lab}.km_survival_90_180_365[{i}]")
        add("Surv" + t + "CI" + n, ci(d["km_ci"][i]), s, f"dynamics.{lab}.km_ci[{i}]")
    add("MaxFollow" + n, f"{d['max_followup_days']:.0f}", s, f"dynamics.{lab}.max_followup_days")
    for kind in ("path", "script", "target", "manifest", "dep"):
        K = kind.capitalize()
        add("Rate" + K + n, f"{d['by_kind'][kind]['rate_per_100cy']:.1f}", s, f"dynamics.{lab}.by_kind.{kind}.rate_per_100cy")
        add("Breaks" + K + n, num(d["by_kind"][kind]["breaks"]), s, f"dynamics.{lab}.by_kind.{kind}.breaks")
        add("Life" + K + n, num(d["by_kind"][kind]["lifetimes"]), s, f"dynamics.{lab}.by_kind.{kind}.lifetimes")
        hk = S["head_by_kind"][lab][kind]
        add("Head" + K + n, num(hk["born_valid"]), s, f"head_by_kind.{lab}.{kind}.born_valid")
        add("HeadViol" + K + n, num(hk["violated"]), s, f"head_by_kind.{lab}.{kind}.violated")
        add("HeadDrift" + K + n, pct(hk["drift"], 2), s, f"head_by_kind.{lab}.{kind}.drift")
        add("HeadAll" + K + n, num(hk["at_head"]), s, f"head_by_kind.{lab}.{kind}.at_head")
    rp = S["repair"][lab]
    add("Episodes" + n, num(rp["break_episodes"]), s, f"repair.{lab}.break_episodes")
    add("EpisodeRepos" + n, num(rp["repos"]), s, f"repair.{lab}.repos")
    add("Exact" + n, num(rp["exact_commit_located"]), s, f"repair.{lab}.exact_commit_located")
    add("Open" + n, num(rp["ends"].get("open", 0)), s, f"repair.{lab}.ends.open")
    add("EditRepair" + n, num(rp["ends"].get("edit_repair", 0)), s, f"repair.{lab}.ends.edit_repair")
    add("RepoRepair" + n, num(rp["ends"].get("repo_repair", 0)), s, f"repair.{lab}.ends.repo_repair")
    add("ShareOpen" + n, pct(rp["share_open_at_head"]), s, f"repair.{lab}.share_open_at_head")
    add("ShareOpenCI" + n, ci(rp["boot_ci_open_7_30_90_touched"][0]), s, f"repair.{lab}.boot_ci_open_7_30_90_touched[0]")
    add("MedRepair" + n, f"{rp['km_median_days_to_repair']:.0f}", s, f"repair.{lab}.km_median_days_to_repair")
    for i, t in enumerate(("Week", "Month", "Quarter")):
        add("Rep" + t + n, pct(rp["repaired_within_7_30_90_days"][i]), s, f"repair.{lab}.repaired_within_7_30_90_days[{i}]")
        add("Rep" + t + "CI" + n, ci(rp["boot_ci_open_7_30_90_touched"][i + 1]), s, f"repair.{lab}.boot_ci_open_7_30_90_touched[{i + 1}]")
    add("MedOpenDays" + n, f"{rp['median_days_open_so_far']:.0f}", s, f"repair.{lab}.median_days_open_so_far")
    add("OpenIQR" + n, f"{rp['iqr_days_open_so_far'][0]:.0f} to {rp['iqr_days_open_so_far'][1]:.0f}", s, f"repair.{lab}.iqr_days_open_so_far")
    add("MedClosedDays" + n, f"{rp['median_days_broken_closed']:.1f}", s, f"repair.{lab}.median_days_broken_closed")
    add("Touched" + n, pct(rp["share_file_touched_in_break_commit"]), s, f"repair.{lab}.share_file_touched_in_break_commit")
    add("TouchedK" + n, num(rp["file_touched_in_break_commit"]), s, f"repair.{lab}.file_touched_in_break_commit")
    cp = S["coupling"][lab]
    add("Sync" + n, num(cp["in_sync_updates"]), s, f"coupling.{lab}.in_sync_updates")
    add("Invalidations" + n, num(cp["invalidations"]), s, f"coupling.{lab}.invalidations")
    add("SyncShare" + n, pct(cp["in_sync_share"]), s, f"coupling.{lab}.in_sync_share")
    add("SyncShareCI" + n, ci(cp["ci"]), s, f"coupling.{lab}.ci")
    add("RemValid" + n, num(cp["removals_by_type"]["removal_valid"]), s, f"coupling.{lab}.removals_by_type.removal_valid")
    add("RemBroken" + n, num(cp["removals_by_type"]["removal_broken"]), s, f"coupling.{lab}.removals_by_type.removal_broken")

rr = S["dynamics"]["rate_ratio_context_over_readme"]
add("RateRatio", f"{rr['estimate']:.2f}", s, "dynamics.rate_ratio_context_over_readme.estimate")
add("RateRatioCI", ci(rr["ci"], 2, 1), s, "dynamics.rate_ratio_context_over_readme.ci")
pd_ = S["paired_diff_context_minus_readme"]
add("DiffSync", f"{-100 * pd_['in_sync_share']['diff']:.1f}", s, "paired_diff_context_minus_readme.in_sync_share.diff (sign flipped)")
add("DiffSyncCI", f"{-100 * pd_['in_sync_share']['ci'][1]:.1f} to {-100 * pd_['in_sync_share']['ci'][0]:.1f}", s, "paired_diff_context_minus_readme.in_sync_share.ci (sign flipped)")
add("DiffOpen", pct(pd_["share_open"]["diff"]), s, "paired_diff_context_minus_readme.share_open.diff")
add("DiffOpenCI", ci(pd_["share_open"]["ci"]), s, "paired_diff_context_minus_readme.share_open.ci")
add("DiffDrift", pct(pd_["pooled_drift"]["diff"], 2), s, "paired_diff_context_minus_readme.pooled_drift.diff")
add("DiffDriftCI", ci(pd_["pooled_drift"]["ci"], 2), s, "paired_diff_context_minus_readme.pooled_drift.ci")
cn = S["concentration"]
add("TopTenShare", pct(cn["top10_repos_share_of_breaks"]), s, "concentration.top10_repos_share_of_breaks")
add("MaxBreaksRepo", num(cn["max_breaks_one_repo"]), s, "concentration.max_breaks_one_repo")
wb = S["who_breaks"]
add("BreakCommits", num(wb["breaking_commits"]), s, "who_breaks.breaking_commits")
add("BreakAgent", num(wb["agent_attributed"]), s, "who_breaks.agent_attributed")
add("BreakAgentShare", pct(wb["share"]), s, "who_breaks.share")
add("BreakAgentCI", ci(wb["wilson"]), s, "who_breaks.wilson")
add("BaseAgentShare", pct(wb["base_share"]), s, "who_breaks.base_share")
bl = S["baselines"]
add("NaiveFlagged", num(bl["single_snapshot_flagged"]), s, "baselines.single_snapshot_flagged")
add("NaiveRate", pct(bl["single_snapshot_rate"]), s, "baselines.single_snapshot_rate")
add("NaiveFiles", pct(bl["single_snapshot_share_files"]), s, "baselines.single_snapshot_share_files")
add("NaiveAnchoredShare", pct(bl["share_of_single_snapshot_flags_that_are_anchored"]), s, "baselines.share_of_single_snapshot_flags_that_are_anchored")
add("TwoSnap", num(bl["two_snapshot_flagged"]), s, "baselines.two_snapshot_flagged")
add("TwoSnapRecall", pct(bl["two_snapshot_recall_of_anchored_head"]), s, "baselines.two_snapshot_recall_of_anchored_head")
add("InvisibleBreaks", pct(bl["share_breaks_invisible_at_head"]), s, "baselines.share_breaks_invisible_at_head")
for r in AGE:
    add("AgeDrift" + {"0": "Zero", "30": "Thirty", "60": "Sixty", "90": "Ninety", "120": "OneTwenty", "180": "OneEighty", "240": "TwoForty", "300": "ThreeHundred", "365": "Year"}[r["age_days"]],
        f"{100 * float(r['mean_drift']):.2f}", "drift_by_age_summary.csv", f"age_days={r['age_days']}.mean_drift")
    if r["age_days"] in ("240", "365", "30"):
        nm = {"240": "TwoForty", "365": "Year", "30": "Thirty"}[r["age_days"]]
        add("AgeDriftCI" + nm, f"{100 * float(r['lo']):.2f} to {100 * float(r['hi']):.2f}", "drift_by_age_summary.csv", f"age_days={r['age_days']}.lo,hi")
        add("AgeFiles" + nm, r["files"], "drift_by_age_summary.csv", f"age_days={r['age_days']}.files")

cs = S["consistency"]
add("RuleFiles", num(cs["files_with_rules"]), s, "consistency.files_with_rules")
add("RuleFilesAll", num(cs["files_analysed"]), s, "consistency.files_analysed")
add("NRules", num(cs["rules"]), s, "consistency.rules")
for k, n in (("unit_pos", "UnitPos"), ("unit_neg", "UnitNeg"), ("horn_definite", "HornDef"), ("horn_negative", "HornNeg"), ("choice", "Choice")):
    add("Rules" + n, num(cs["forms"][k]), s, f"consistency.forms.{k}")
add("HornShare", pct(cs["horn_share"]), s, "consistency.horn_share")
add("HornLower", pct(cs["horn_share_wilson"][0], 2), s, "consistency.horn_share_wilson[0]")
add("MedRules", f"{cs['median_rules_per_file']:.0f}", s, "consistency.median_rules_per_file")
add("MaxRules", num(cs["max_rules_per_file"]), s, "consistency.max_rules_per_file")
add("UnsatFiles", num(cs["files_unsat"]), s, "consistency.files_unsat")
add("UnsatShare", pct(cs["share_files_unsat"]), s, "consistency.share_files_unsat")
add("UnsatCI", ci(cs["share_files_unsat_wilson"]), s, "consistency.share_files_unsat_wilson")
add("RawOr", cs["raw_or_pairs"], s, "consistency.raw_or_pairs")
add("RawOrNeg", cs["raw_or_pairs_in_prohibitions"], s, "consistency.raw_or_pairs_in_prohibitions")
add("NCores", num(cs["cores"]), s, "consistency.cores")
v = "validation_summary.json"
add("ConfGroups", V["conflicts"]["groups"], v, "conflicts.groups")
add("ConfFiles", V["conflicts"]["files"], v, "conflicts.files")
add("ConfTrue", V["conflicts"]["true_contradictions"], v, "conflicts.true_contradictions")
add("ConfScoped", V["conflicts"]["labels"].get("qualified by scope, role or time", 0), v, "conflicts.labels[qualified]")
add("ConfExtract", V["conflicts"]["labels"].get("extraction error or descriptive text", 0), v, "conflicts.labels[extraction]")
add("ConfUpper", pct(V["conflicts"]["precision_upper_wilson"]), v, "conflicts.precision_upper_wilson")
add("ValAN", V["extraction"]["n"], v, "extraction.n")
add("ValAK", V["extraction"]["genuine"], v, "extraction.genuine")
add("ValAPrec", pct(V["extraction"]["precision"], 0), v, "extraction.precision")
add("ValACI", ci(V["extraction"]["wilson"], 0), v, "extraction.wilson")
add("ValAViol", V["extraction"]["violated_in_sample"], v, "extraction.violated_in_sample")
add("ValAViolNotAnch", V["extraction"]["violated_not_anchored"], v, "extraction.violated_not_anchored")
add("ValBN", V["breaks"]["n"], v, "breaks.n")
add("ValBK", V["breaks"]["true_staleness"], v, "breaks.true_staleness")
add("ValBPrec", pct(V["breaks"]["precision"], 0), v, "breaks.precision")
add("ValBCI", ci(V["breaks"]["wilson"], 0), v, "breaks.wilson")
add("ValCN", V["never_valid"]["n"], v, "never_valid.n")
for k, n in (("untracked or generated artefact", "Untracked"), ("external to the repository", "External"),
             ("example, template or file to be created", "Example"), ("plausibly wrong repository reference", "Wrong"), ("not a path", "NotPath")):
    add("ValC" + n, V["never_valid"]["categories"][k]["count"], v, f"never_valid.categories[{k}].count")
    add("ValC" + n + "Pct", pct(V["never_valid"]["categories"][k]["share"], 0), v, f"never_valid.categories[{k}].share")
add("ValCWrongCI", ci(V["never_valid"]["categories"]["plausibly wrong repository reference"]["wilson"], 0), v, "never_valid.categories[plausibly wrong].wilson")
if L:
    l = "llm_second_rater_summary.json"
    add("LlmModel", L["model"].replace("_", "\\_"), l, "model")
    add("LlmCalls", L["calls_total"], l, "calls_total")
    for sset in "AB":
        add("LlmAgree" + sset, pct(L[sset]["raw_agreement"], 0), l, f"{sset}.raw_agreement")
        add("LlmKappa" + sset, f"{L[sset]['cohen_kappa']:.2f}", l, f"{sset}.cohen_kappa")

cm = S["compliance"]
add("CCRuleRepos", num(cm["repos_with_rule"]), s, "compliance.repos_with_rule")
add("CCNoRuleRepos", num(cm["repos_without_rule"]), s, "compliance.repos_without_rule")
po = cm["with_rule_post_only"]
add("CCPostRepos", num(po["repos"]), s, "compliance.with_rule_post_only.repos")
add("CCPostMean", pct(po["mean_compliance"]), s, "compliance.with_rule_post_only.mean_compliance")
add("CCPostMedian", pct(po["median_compliance"]), s, "compliance.with_rule_post_only.median_compliance")
add("CCPostCommits", num(po["pooled_commits"]), s, "compliance.with_rule_post_only.pooled_commits")
add("CCBelowHalf", pct(po["share_repos_below_half"]), s, "compliance.with_rule_post_only.share_repos_below_half")
add("CCAboveNinety", pct(po["share_repos_at_least_90"]), s, "compliance.with_rule_post_only.share_repos_at_least_90")
for lab, n in (("with_rule_pre_post", "Rule"), ("without_rule_pre_post", "NoRule")):
    x = cm[lab]
    add("CCPP" + n + "Repos", num(x["repos"]), s, f"compliance.{lab}.repos")
    add("CCPre" + n, pct(x["mean_pre"]), s, f"compliance.{lab}.mean_pre")
    add("CCPost" + n, pct(x["mean_post"]), s, f"compliance.{lab}.mean_post")
    add("CCDiff" + n, pct(x["mean_diff"]), s, f"compliance.{lab}.mean_diff")
    add("CCDiffCI" + n, ci(x["diff_ci"]), s, f"compliance.{lab}.diff_ci")
g = cm["gain_difference_rule_minus_no_rule"]
add("CCGainDiff", pct(g["estimate"]), s, "compliance.gain_difference_rule_minus_no_rule.estimate")
add("CCGainDiffCI", ci(g["ci"]), s, "compliance.gain_difference_rule_minus_no_rule.ci")
add("CCRuleAtCreation", pct(cm["rule_at_creation_share"]), s, "compliance.rule_at_creation_share")
ag = cm["agent_vs_other_after_rule"]
add("CCAgentRepos", num(ag["repos"]), s, "compliance.agent_vs_other_after_rule.repos")
add("CCAgentMean", pct(ag["mean_agent"]), s, "compliance.agent_vs_other_after_rule.mean_agent")
add("CCOtherMean", pct(ag["mean_other"]), s, "compliance.agent_vs_other_after_rule.mean_other")
add("CCAgentDiff", pct(ag["mean_diff"]), s, "compliance.agent_vs_other_after_rule.mean_diff")
add("CCAgentDiffCI", ci(ag["diff_ci"]), s, "compliance.agent_vs_other_after_rule.diff_ci")
add("CCAgentP", f"{ag['wilcoxon_p']:.3f}", s, "compliance.agent_vs_other_after_rule.wilcoxon_p")
add("AgentCommitShare", pct(wb["all_repos_agent_share"]), s, "who_breaks.all_repos_agent_share")
add("OvVersions", OV["n_versions"], "overview_example.json", "n_versions")
add("OvAge", f"{OV['age_days']:.0f}", "overview_example.json", "age_days")
add("OvCons", OV["n_constraints_head"], "overview_example.json", "n_constraints_head")

# ------------------------------------------------------------------ round 1 revision: robustness, kit, panel check
R = json.load(open(os.path.join(RES, "robustness.json")))
KS = json.load(open(os.path.join(ART, "labelling", "kit_summary.json")))
r = "robustness.json"


def est(path, name, d=1, scale=100.0, neg=False):
    node = R
    for k in path.split("."):
        node = node[k]
    sgn = -1 if neg else 1
    add(name, f"{sgn * scale * node['est']:.{d}f}", r, path + ".est" + (" (sign flipped)" if neg else ""))
    lo, hi = sorted([sgn * scale * node["ci"][0], sgn * scale * node["ci"][1]])
    add(name + "CI", f"{lo:.{d}f} to {hi:.{d}f}", r, path + ".ci" + (" (sign flipped)" if neg else ""))


def val(path, name, fmt="{:.1f}", scale=1.0, file=r, root=None):
    node = R if root is None else root
    for k in path.split("."):
        node = node[int(k)] if isinstance(node, list) else node[k]
    add(name, fmt.format(scale * node) if not isinstance(node, str) else node, file, path)


for lab, n in (("context", "Ctx"), ("readme", "Rd")):
    est(f"invalidation.{lab}_invalidation_rate", "InvRate" + n, 1, 1)
    est(f"invalidation.{lab}_insync_rate", "SyncRate" + n, 1, 1)
    val(f"invalidation.implied_half_life_years.{lab}", "InvHalf" + n)
    val(f"invalidation.counts.{lab}.in_sync", "AnchSync" + n, "{:.0f}")
est("invalidation.invalidation_ratio_ctx_over_readme", "InvRatio", 2, 1)
est("invalidation_entry_observed.invalidation_ratio_ctx_over_readme", "InvRatioEntry", 2, 1)
est("invalidation_entry_observed.readme_invalidation_rate", "InvRateRdEntry", 1, 1)
est("invalidation_entry_observed.break_ratio_ctx_over_readme", "BreakRatioEntry", 2, 1)
est("invalidation_paths_only.invalidation_ratio_ctx_over_readme", "InvRatioPaths", 2, 1)
val("invalidation.share_readme_left_truncated", "ShareRdTrunc", "{:.0f}", 100)
for key, n in (("context", "Ctx"), ("readme_entry_observed", "Rd")):
    for cause, c in (("break", "Break"), ("sync_removal", "Sync"), ("removal_valid", "RemValid"), ("invalidated", "Inv"), ("event_free", "Free")):
        est(f"cif.{key}_{cause}_365", "Cif" + c + "Year" + n)
    est(f"cif.{key}_invalidated_90", "CifInvNinety" + n)
val("cif.n.readme_entry_observed", "CifNRd", "{:,.0f}")
est("insync.event_level.diff", "SyncDiff", neg=True)
for key, n in (("commit_level", "SyncCommit"), ("quick_repair_one_day_as_in_sync", "SyncDay"), ("quick_repair_three_commits_as_in_sync", "SyncThree")):
    est(f"insync.{key}.context", n + "Ctx")
    est(f"insync.{key}.readme", n + "Rd")
    est(f"insync.{key}.diff", n + "Diff", neg=True)
val("insync.commit_level.context_commits.est", "InvCommitsCtx", "{:.0f}")
val("insync.commit_level.readme_commits.est", "InvCommitsRd", "{:.0f}")
for lab, n in (("context", "Ctx"), ("readme", "Rd")):
    val(f"insync.quick_counts.{lab}.closed", "Closed" + n, "{:.0f}")
    val(f"insync.quick_counts.{lab}.closed_within_one_day", "ClosedDay" + n, "{:.0f}")
    val(f"insync.insync_repo_mean.{lab}", "SyncRepoMean" + n, "{:.1f}", 100)
    val(f"insync.insync_repo_mean.{lab}_repos", "SyncRepoN" + n, "{:.0f}")
    val(f"open.repo_mean.{lab}", "OpenRepoMean" + n, "{:.1f}", 100)
    val(f"open.older_counts.{lab}", "OldBreaks" + n, "{:.0f}")
    est(f"open.breaks_older_than_30_days.{lab}", "OpenOld" + n)
est("open.breaks_older_than_30_days.diff", "OpenOldDiff")
for pre, n in (("insync.insync_", "Sync"), ("open.", "Open")):
    sg = -100 if n == "Sync" else 100
    val(pre + "both_sides.repos", n + "BothRepos", "{:.0f}")
    val(pre + "both_sides.mean_diff", n + "BothMean", "{:.1f}", sg)
    val(pre + "both_sides.median_diff", n + "BothMedian", "{:.1f}", abs(sg))
    val(pre + "both_sides.wilcoxon_p", n + "BothP", "{:.3f}")
    lo_, hi_ = sorted([sg * R[pre.split(".")[0]][pre.split(".")[1] + "leave_one_out"]["min"], sg * R[pre.split(".")[0]][pre.split(".")[1] + "leave_one_out"]["max"]])
    add(n + "LooRange", f"{lo_:.1f} to {hi_:.1f}", r, pre + "leave_one_out.min,max")
    for t in ("2", "5"):
        blk = R[pre.split(".")[0]][pre.split(".")[1] + f"trimmed_top{t}_each_side"]
        tn = {"2": "Two", "5": "Five"}[t]
        add(n + "Trim" + tn, f"{sg * blk['diff']:.1f}", r, pre + f"trimmed_top{t}_each_side.diff")
        lo_, hi_ = sorted([sg * blk["ci"][0], sg * blk["ci"][1]])
        add(n + "Trim" + tn + "CI", f"{lo_:.1f} to {hi_:.1f}", r, pre + f"trimmed_top{t}_each_side.ci")
        add(n + "Trim" + tn + "Ctx", f"{100 * blk['context']:.1f}", r, pre + f"trimmed_top{t}_each_side.context")
        add(n + "Trim" + tn + "Rd", f"{100 * blk['readme']:.1f}", r, pre + f"trimmed_top{t}_each_side.readme")
val("insync.insync_concentration.readme_top2_share_of_events", "RdTopTwoShare", "{:.0f}", 100)
val("repair_mode.rewritten_to_valid_target", "RewrittenK", "{:.0f}")
val("repair_mode.deleted", "DeletedK", "{:.0f}")
val("repair_mode.classified", "RepairClassified", "{:.0f}")
val("repair_mode.rewritten_share", "RewrittenShare", "{:.0f}", 100)
for lab, n in (("context", "Ctx"), ("readme", "Rd")):
    for g, gn in (("slashed_paths", "Slashed"), ("bare_names", "Bare"), ("non_path", "NonPath"), ("directory_paths", "Dir"), ("file_paths", "FilePath")):
        val(f"drift_sens.{lab}.{g}.drift", "Drift" + gn + n, "{:.2f}", 100)
        val(f"drift_sens.{lab}.{g}.rate_per_100cy", "Rate" + gn + n, "{:.1f}")
        val(f"drift_sens.{lab}.{g}.anchored_at_head", "Anch" + gn + n, "{:,.0f}")
        val(f"drift_sens.{lab}.{g}.violated", "Viol" + gn + n, "{:.0f}")
        val(f"drift_sens.{lab}.{g}.breaks", "Breaks" + gn + n, "{:.0f}")
    val(f"drift_sens.{lab}.share_bare_among_head_paths", "ShareBare" + n, "{:.0f}", 100)
    val(f"drift_sens.{lab}.share_lenient_only_at_birth", "ShareLenientBirth" + n, "{:.0f}", 100)
    val(f"lenient.{lab}.exact_path_gone_but_lenient_match", "Hidden" + n, "{:.0f}")
    val(f"lenient.{lab}.violated_lenient", "HiddenBase" + n, "{:.0f}")
    val(f"lenient.{lab}.strictly_anchored_paths_at_head", "StrictPaths" + n, "{:,.0f}")
    val(f"lenient.{lab}.drift_lenient", "LenientDrift" + n, "{:.2f}", 100)
    val(f"lenient.{lab}.drift_if_all_hidden_are_real", "UpperDrift" + n, "{:.2f}", 100)
    for k2, kn, f2, sc in (("drift", "EnumDrift", "{:.2f}", 100), ("break_rate", "EnumRate", "{:.1f}", 1), ("invalidation_rate", "EnumInvRate", "{:.1f}", 1),
                           ("insync_share", "EnumSync", "{:.1f}", 100), ("open_share", "EnumOpen", "{:.1f}", 100), ("breaks", "EnumBreaks", "{:.0f}", 1)):
        val(f"enumerated.{lab}.{k2}", kn + n, f2, sc)
    val(f"denominators.{lab}.share_of_all_files", "HitAll" + n, "{:.1f}", 100)
    val(f"denominators.{lab}.files_hit", "HitK" + n, "{:.0f}")
    val(f"denominators.{lab}.files_with_anchored", "HitDen" + n, "{:.0f}")
add("HitAllCICtx", ci(R["denominators"]["context"]["wilson_all"]), r, "denominators.context.wilson_all")
for k, n in (("AGENTS.md", "Agents"), ("CLAUDE.md", "Claude"), (".cursorrules", "Cursor"), ("copilot-instructions.md", "Copilot")):
    add("HitAll" + n, pct(R["denominators"][k]["share_of_all_files"]), r, f"denominators.{k}.share_of_all_files")
    add("HitDen" + n, R["denominators"][k]["files_with_anchored"], r, f"denominators.{k}.files_with_anchored")
    add("HitK" + n, R["denominators"][k]["files_hit"], r, f"denominators.{k}.files_hit")
val("enumerated.repos", "EnumRepos", "{:.0f}")
add("NSampledRepos", int(C["repos"]) - R["enumerated"]["repos"], r, "corpus.repos minus enumerated.repos")
a240 = R["age"]["all_files"][-1]
add("AgeEndDays", a240["age"], r, "age.all_files[-1].age")
add("AgeStartDays", R["age"]["all_files"][1]["age"], r, "age.all_files[1].age")
c = R["age"]["cohort_240"]
add("AgeFilesDriftTwoForty", a240["files_with_drift"], r, "age.all_files[240].files_with_drift")
add("AgeFilesTwoFortyAll", a240["files"], r, "age.all_files[240].files")
for row in c:
    if row["age"] in (30, 90, 180, 240):
        add("Cohort" + {30: "Thirty", 90: "Ninety", 180: "OneEighty", 240: "TwoForty"}[row["age"]], f"{100 * row['mean_drift']:.2f}", r, f"age.cohort_240[{row['age']}].mean_drift")
add("RulesCmdMention", num(cs["unit_pos_from_command_mentions"]), s, "consistency.unit_pos_from_command_mentions")
add("RulesCmdShare", pct(cs["unit_pos_from_command_mentions"] / cs["forms"]["unit_pos"], 0), s, "consistency.unit_pos_from_command_mentions / forms.unit_pos")
add("RulesAxioms", num(cs["axioms"]), s, "consistency.axioms")
k = "labelling/kit_summary.json"
add("KitA", sum(v["sampled"] for kk, v in KS.items() if kk.startswith("A_")), k, "sum of A_*.sampled")
add("KitAViol", KS["A_anchored_violated"]["sampled"], k, "A_anchored_violated.sampled")
add("KitBCtx", KS["B_context_non_path"]["sampled"] + KS["B_context_path"]["sampled"], k, "B_context_*.sampled")
add("KitBRd", KS["B_readme_non_path"]["sampled"] + KS["B_readme_path"]["sampled"], k, "B_readme_*.sampled")
add("KitS", KS["S_context"]["sampled"], k, "S_context.sampled (same for README)")
add("KitRFiles", KS["R"]["files"], k, "R.files")
add("KitRLines", KS["R"]["lines"], k, "R.lines")
add("KitL", KS["L"]["sampled"], k, "L.sampled")
add("KitCalib", KS["calibration_items"], k, "calibration_items")
# round 2: form stratification, like-for-like ratios, at-risk counts
est("invalidation_entry_observed.readme_break_rate", "RateRdEntry", 1, 1)
est("invalidation_paths_only.break_ratio_ctx_over_readme", "BreakRatioPaths", 2, 1)
est("invalidation_entry_observed.readme_insync_rate", "SyncRateRdEntry", 1, 1)
val("cif.n.readme_entry_observed", "LifeRdEntry", "{:,.0f}")
est("form.rates_code_span.break_ratio", "BreakRatioSpan", 2, 1)
est("form.rates_code_span.invalidation_ratio", "InvRatioSpan", 2, 1)
for lab, n in (("context", "Ctx"), ("readme", "Rd")):
    for f_, fn in (("link", "Link"), ("code_span", "Span"), ("command", "Cmd")):
        val(f"form.composition_anchored.{lab}.{f_}", "Comp" + fn + n, "{:.0f}", 100)
        val(f"form.insync_by_form.strata.{f_}.{lab}_share", "SyncForm" + fn + n, "{:.1f}", 100)
        val(f"form.insync_by_form.strata.{f_}.{lab}_n", "SyncFormN" + fn + n, "{:.0f}")
        val(f"form.open_by_form.strata.{f_}.{lab}_share", "OpenForm" + fn + n, "{:.1f}", 100)
        val(f"form.open_by_form.strata.{f_}.{lab}_n", "OpenFormN" + fn + n, "{:.0f}")
    val(f"form.composition_target.{lab}.doc_file", "CompDoc" + n, "{:.0f}", 100)
    val(f"bulk_rewrites.{lab}.share_bulk", "BulkShare" + n, "{:.0f}", 100)
    val(f"bulk_rewrites.{lab}.insync_share_without_bulk", "SyncNoBulk" + n, "{:.1f}", 100)
    val(f"readded_keys.{lab}.of_which_key_live_at_head", "Readded" + n, "{:,.0f}")
for f_, fn in (("link", "Link"), ("code_span", "Span"), ("command", "Cmd")):
    val(f"form.insync_by_form.strata.{f_}.diff", "SyncFormDiff" + fn, "{:.1f}", 100)
    val(f"form.open_by_form.strata.{f_}.diff", "OpenFormDiff" + fn, "{:.1f}", 100)
add("SyncFormDiffSpanCI", ci(R["form"]["insync_by_form"]["strata"]["code_span"]["diff_ci"]), r, "form.insync_by_form.strata.code_span.diff_ci")
add("OpenFormDiffSpanCI", ci(R["form"]["open_by_form"]["strata"]["code_span"]["diff_ci"]), r, "form.open_by_form.strata.code_span.diff_ci")
est("form.insync_by_form.stratified_diff", "SyncStratForm")
est("form.open_by_form.stratified_diff", "OpenStratForm")
est("form.insync_by_target.stratified_diff", "SyncStratTarget")
est("form.open_by_target.stratified_diff", "OpenStratTarget")
est("form.without_links_to_doc_files.insync_diff", "SyncNoDocLinks")
est("form.without_links_to_doc_files.open_diff", "OpenNoDocLinks")
val("bulk_rewrites.diff_without_bulk", "SyncNoBulkDiff", "{:.1f}", 100)
add("SyncNoBulkDiffCI", ci(R["bulk_rewrites"]["diff_without_bulk_ci"]), r, "bulk_rewrites.diff_without_bulk_ci")
for kind, n in (("insync", "Sync"), ("open", "Open")):
    w_ = R["within_repo"][kind]
    add(n + "SignFor", w_["favours_headline_direction"], r, f"within_repo.{kind}.favours_headline_direction")
    add(n + "SignAgainst", w_["opposite"], r, f"within_repo.{kind}.opposite")
    add(n + "SignTies", w_["ties"], r, f"within_repo.{kind}.ties")
    add(n + "SignP", f"{w_['sign_test_p']:.3f}", r, f"within_repo.{kind}.sign_test_p")
for key, n in (("context", "Ctx"), ("readme_entry_observed", "Rd")):
    for cause, c in (("break", "Break"), ("sync_removal", "Sync"), ("removal_valid", "RemValid"), ("invalidated", "Inv")):
        est(f"cif.{key}_{cause}_180", "Cif" + c + "HalfYear" + n)
    for m_, mn in (("180", "HalfYear"), ("365", "Year")):
        val(f"at_risk.{key}.{m_}.at_risk", "AtRisk" + mn + n, "{:,.0f}")
        val(f"at_risk.{key}.{m_}.files", "AtRiskFiles" + mn + n, "{:.0f}")
    val(f"at_risk.{key}.median_followup_days", "MedFollow" + n, "{:.0f}")
val("head_partition.entered_invalid_later_valid", "EnteredInvalid", "{:.0f}")
val("head_partition.lifetimes_not_anchored", "LifeNotAnch", "{:,.0f}")
o = "overview_example.json"
add("OvBreaks", OV["break_episodes"], o, "break_episodes")
add("OvRows", OV["rows_shown"], o, "rows_shown")
add("OvLargestDay", OV["largest_break_day"], o, "largest_break_day")
add("OvFirstBreakDays", OV["first_break_days_after_creation"], o, "first_break_days_after_creation")
add("OvOpen", OV["open_at_head"], o, "open_at_head")
add("OvMinStay", OV["min_days_in_file_after_break"], o, "min_days_in_file_after_break")
add("OvMaxStay", OV["max_days_in_file_after_break"], o, "max_days_in_file_after_break")
add("OvMarchBreaks", sum(v for d_, v in OV["breaks_by_day"].items() if d_.startswith("2026-03")), o, "breaks_by_day (March 2026)")
add("OvAprilBreaks", sum(v for d_, v in OV["breaks_by_day"].items() if d_.startswith("2026-04")), o, "breaks_by_day (April 2026)")
add("CCPostPooled", pct(cm["with_rule_post_only"]["pooled_share"]), s, "compliance.with_rule_post_only.pooled_share")

# Additional review analyses, generated from the shipped timelines.
IC = json.load(open(os.path.join(RES, "instruction_coverage.json")))
for k, n in (("nested", "NestedRepos"), ("rule_files", "RuleRepos"), ("import_candidates", "ImportRepos"), ("any", "DelegatingRepos")):
    add(n, IC["counts"][k], "instruction_coverage.json", "counts." + k)

for kind, name in (("insync", "SyncRepoForm"), ("open", "OpenRepoForm")):
    est("repository_by_form." + kind, name)
    val("repository_by_form." + kind + ".matched_repositories", name + "Repos", "{:.0f}")
PD = json.load(open(os.path.join(RES, "precision_design.json")))
for sheet, name in (("B_breaks", "PrecisionGapBreak"), ("S_insync", "PrecisionGapSync")):
    key = "detectable_gap_80pct_two_sided_5pct_conservative"
    add(name, f"{100 * PD[sheet][key]:.0f}", "precision_design.json", sheet + "." + key)
for field, name in (("mean", "AlarmMean"), ("median", "AlarmMedian"), ("max", "AlarmMax")):
    val("alarm_burden." + field, name, "{:.2f}" if field == "mean" else "{:.0f}")
add("MedOpenExact", f"{S['repair']['context']['median_days_open_so_far']:.1f}", s, "repair.context.median_days_open_so_far")
add("OpenIQR", " to ".join(f"{x:.0f}" for x in S['repair']['context']['iqr_days_open_so_far']), s, "repair.context.iqr_days_open_so_far")
for ft, suffix in (("AGENTS.md", "Agents"), ("CLAUDE.md", "Claude")):
    for field, name in (("break_rate", "TypeBreak"), ("invalidation_rate", "TypeInv")):
        add(name + suffix, f"{R['dynamics_by_file_type'][ft][field]:.1f}", r, "dynamics_by_file_type[" + ft + "]." + field)
for art, suffix in (("context", "Ctx"), ("readme", "Rd")):
    val("presence_spells." + art + ".break_rate_per_100_years", "SpellBreak" + suffix)
    val("presence_spells." + art + ".invalidation_rate_per_100_years", "SpellInv" + suffix)

names = [m[0] for m in M]
assert len(names) == len(set(names)), [n for n in names if names.count(n) > 1]
with open(OUT, "w") as f:
    f.write("% Generated by the artifact. Do not edit by hand.\n")
    for name, val, _, _ in M:
        f.write(f"\\newcommand{{\\n{name}}}{{{val}}}\n")
with open(os.path.join(ART, "claims.md"), "w") as f:
    f.write("# Claims\n\nEvery number in the manuscript is a LaTeX macro defined in the generated numbers file. "
            "This table maps each macro to the results file and key it is read from. "
            "All results files are produced by `bash run.sh` (stages 4 to 9); the per-stage command is listed in the README.\n\n"
            "| Macro | Value | Results file | Key | Produced by |\n|---|---|---|---|---|\n")
    prod = {"summary.json": "src/s4_analyze.py", "repos.csv": "src/s4_analyze.py", "validation_summary.json": "src/s7_validation_summary.py",
            "llm_second_rater_summary.json": "src/s8_llm_second_rater.py", "drift_by_age_summary.csv": "src/s6_figures.py",
            "overview_example.json": "src/s6_figures.py"}
    import glob, re as _re
    tex = "".join(open(p).read() for p in glob.glob(os.path.join(os.path.dirname(ART), "manuscript", "sections", "*.tex")) + [os.path.join(os.path.dirname(ART), "manuscript", "main.tex")])
    used = set(_re.findall(r"\\n([A-Z][A-Za-z]+)", tex))
    prod.update({"precision_design.json": "src/s4c_revision.py", "instruction_coverage.json": "src/instruction_census.py --clones /path/to/clones", "robustness.json": "src/s4b_robustness.py", "labelling/kit_summary.json": "src/s10_labelling_kit.py"})
    nused = 0
    for name, val, src, key in M:
        if name not in used:
            continue
        nused += 1
        loc = src if src.startswith("labelling/") else "results/" + src
        producer = prod[src]
        if src == "robustness.json" and key.split(".")[0].split("[")[0] in {"repository_by_form", "presence_spells", "alarm_burden", "dynamics_by_file_type"}:
            producer = "src/s4c_revision.py"
        f.write(f"| `\\n{name}` | {val.replace('{,}', ',')} | {loc} | `{key}` | `python3 {producer}` |\n")
    undefined = sorted(u for u in used if u not in {m[0] for m in M})
    print("macros used in the manuscript:", nused, "| used but undefined:", undefined)
with open(os.path.join(ART, "claims.md"), "a") as f:
    f.write("""
## Numbers typed by hand in the text

| Claim | Source |
|---|---|
| Inclusion filter: at least 50 stars, at most 150 MB, four file names, six size bands from 500 to 60,000 bytes, first two ranked pages of 100 per query (API cap 1,000), 4,800 of 1,834,808 reported hits | constants in `src/s1_search.py` and `src/s2_select.py`; `results/summary.json` key `funnel` |
| Up to 150 evenly spaced snapshots, bootstrap resamples (2,000, 1,000 and 500, see `results/robustness.json` key `bootstrap_resamples`), ten or more references for a bulk rewrite, breaks older than 30 days, repair within one day or three commits, top two and top five repositories | constants in `src/s3_mine.py`, `src/s4_analyze.py`, `src/s4b_robustness.py` |
| "about twice as often", "about half as often", "one reference in a hundred", "half as much again" | rounded restatements of `nInvRatio`, `nDriftCtx`, `nUpperDriftCtx` over `nLenientDriftCtx` |
| "March 2026", "April 2026" in the worked example | `results/overview_example.json` key `breaks_by_day` |
| Human-derived numbers (macros starting with `h`) | `../manuscript/human_numbers.tex`, written by `src/s11_labelling_agreement.py` from the rater sheets. All render as [PENDING] until the sheets are filled and adjudicated |
| Numbers attributed to other papers (1.27%, 18,048, 230, 612, 356, 23.0%, 32 of 50, 28.9%, 82.3%, over 20%, 124 and 10, 16 of 28, corpus sizes) | the cited papers; those of Treude and Baltes, Tan et al., Gloaguen et al. and dos Santos et al. were read from the PDFs on 4 Oct 2026, see `citation_audit.md` |
""")
print(len(M), "macros written")

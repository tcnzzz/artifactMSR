# Claims

Every number in the manuscript is a LaTeX macro defined in the generated numbers file. This table maps each macro to the results file and key it is read from. All results files are produced by `bash run.sh` (stages 4 to 9); the per-stage command is listed in the README.

| Macro | Value | Results file | Key | Produced by |
|---|---|---|---|---|
| `\nNHits` | 4,800 | results/summary.json | `funnel.search_hits` | `python3 src/s4_analyze.py` |
| `\nNRootRepos` | 3,346 | results/summary.json | `funnel.repos_with_root_file` | `python3 src/s4_analyze.py` |
| `\nNRepos` | 542 | results/summary.json | `corpus.repos` | `python3 src/s4_analyze.py` |
| `\nNCtxFiles` | 755 | results/summary.json | `corpus.context_files` | `python3 src/s4_analyze.py` |
| `\nNReadme` | 523 | results/summary.json | `corpus.readme_files` | `python3 src/s4_analyze.py` |
| `\nNFilesAgents` | 286 | results/summary.json | `corpus.files_by_type.AGENTS.md` | `python3 src/s4_analyze.py` |
| `\nDriftAgents` | 0.71 | results/summary.json | `head_drift.AGENTS.md.pooled_drift` | `python3 src/s4_analyze.py` |
| `\nDriftCIAgents` | 0.41 to 1.08 | results/summary.json | `head_drift.AGENTS.md.pooled_drift_ci` | `python3 src/s4_analyze.py` |
| `\nAnchAgents` | 5,184 | results/summary.json | `head_drift.AGENTS.md.born_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nViolAgents` | 37 | results/summary.json | `head_drift.AGENTS.md.violated_at_head` | `python3 src/s4_analyze.py` |
| `\nNFilesClaude` | 289 | results/summary.json | `corpus.files_by_type.CLAUDE.md` | `python3 src/s4_analyze.py` |
| `\nDriftClaude` | 1.43 | results/summary.json | `head_drift.CLAUDE.md.pooled_drift` | `python3 src/s4_analyze.py` |
| `\nDriftCIClaude` | 0.81 to 2.32 | results/summary.json | `head_drift.CLAUDE.md.pooled_drift_ci` | `python3 src/s4_analyze.py` |
| `\nAnchClaude` | 4,548 | results/summary.json | `head_drift.CLAUDE.md.born_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nViolClaude` | 65 | results/summary.json | `head_drift.CLAUDE.md.violated_at_head` | `python3 src/s4_analyze.py` |
| `\nNFilesCursor` | 135 | results/summary.json | `corpus.files_by_type..cursorrules` | `python3 src/s4_analyze.py` |
| `\nDriftCursor` | 2.50 | results/summary.json | `head_drift..cursorrules.pooled_drift` | `python3 src/s4_analyze.py` |
| `\nDriftCICursor` | 0.76 to 4.95 | results/summary.json | `head_drift..cursorrules.pooled_drift_ci` | `python3 src/s4_analyze.py` |
| `\nAnchCursor` | 679 | results/summary.json | `head_drift..cursorrules.born_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nViolCursor` | 17 | results/summary.json | `head_drift..cursorrules.violated_at_head` | `python3 src/s4_analyze.py` |
| `\nNFilesCopilot` | 45 | results/summary.json | `corpus.files_by_type.copilot-instructions.md` | `python3 src/s4_analyze.py` |
| `\nDriftCopilot` | 0.78 | results/summary.json | `head_drift.copilot-instructions.md.pooled_drift` | `python3 src/s4_analyze.py` |
| `\nDriftCICopilot` | 0.19 to 1.49 | results/summary.json | `head_drift.copilot-instructions.md.pooled_drift_ci` | `python3 src/s4_analyze.py` |
| `\nAnchCopilot` | 516 | results/summary.json | `head_drift.copilot-instructions.md.born_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nViolCopilot` | 4 | results/summary.json | `head_drift.copilot-instructions.md.violated_at_head` | `python3 src/s4_analyze.py` |
| `\nMedStars` | 128 | results/summary.json | `corpus.median_stars` | `python3 src/s4_analyze.py` |
| `\nStarsIQR` | 77 to 313 | results/summary.json | `corpus.stars_iqr` | `python3 src/s4_analyze.py` |
| `\nMedAge` | 133 | results/summary.json | `corpus.median_age_days` | `python3 src/s4_analyze.py` |
| `\nAgeIQR` | 43 to 218 | results/summary.json | `corpus.age_iqr` | `python3 src/s4_analyze.py` |
| `\nShareSingleVersion` | 41.9 | results/summary.json | `corpus.share_single_version` | `python3 src/s4_analyze.py` |
| `\nNSnapshots` | 39,166 | results/summary.json | `corpus.total_snapshots` | `python3 src/s4_analyze.py` |
| `\nNFullEnum` | 430 | results/summary.json | `corpus.fully_enumerated_repos` | `python3 src/s4_analyze.py` |
| `\nNLifeCtx` | 15,620 | results/summary.json | `corpus.constraint_lifetimes_ctx` | `python3 src/s4_analyze.py` |
| `\nLangTop` | TypeScript (130), Python (115), JavaScript (47), Rust (38), Go (32) | results/summary.json | `corpus.languages_top` | `python3 src/s4_analyze.py` |
| `\nNWindowCommits` | 73,959 | results/repos.csv | `sum of window_commits` | `python3 src/s4_analyze.py` |
| `\nConsHeadCtx` | 12,498 | results/summary.json | `head_drift.context.constraints_at_head` | `python3 src/s4_analyze.py` |
| `\nMedConsCtx` | 12 | results/summary.json | `head_drift.context.median_constraints_per_file` | `python3 src/s4_analyze.py` |
| `\nFilesWithConsCtx` | 653 | results/summary.json | `head_drift.context.files_with_constraints` | `python3 src/s4_analyze.py` |
| `\nAnchCtx` | 10,927 | results/summary.json | `head_drift.context.born_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nViolCtx` | 123 | results/summary.json | `head_drift.context.violated_at_head` | `python3 src/s4_analyze.py` |
| `\nDriftCtx` | 1.13 | results/summary.json | `head_drift.context.pooled_drift` | `python3 src/s4_analyze.py` |
| `\nDriftCICtx` | 0.76 to 1.58 | results/summary.json | `head_drift.context.pooled_drift_ci` | `python3 src/s4_analyze.py` |
| `\nAnyViolCtx` | 10.9 | results/summary.json | `head_drift.context.share_files_any_violation` | `python3 src/s4_analyze.py` |
| `\nNeverValidCtx` | 1,448 | results/summary.json | `head_drift.context.never_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nShareNeverCtx` | 11.6 | results/summary.json | `head_drift.context.share_never_valid` | `python3 src/s4_analyze.py` |
| `\nRepoAnyCtx` | 12.9 | results/summary.json | `repo_level.context.share` | `python3 src/s4_analyze.py` |
| `\nRepoAnyKCtx` | 63 | results/summary.json | `repo_level.context.repos_any_violation` | `python3 src/s4_analyze.py` |
| `\nRepoAnyNCtx` | 489 | results/summary.json | `repo_level.context.repos` | `python3 src/s4_analyze.py` |
| `\nEverBrokenCtx` | 16.6 | results/summary.json | `ever_broken.context.share` | `python3 src/s4_analyze.py` |
| `\nEverBrokenKCtx` | 108 | results/summary.json | `ever_broken.context.files_ever_broken` | `python3 src/s4_analyze.py` |
| `\nEverBrokenNCtx` | 652 | results/summary.json | `ever_broken.context.files_with_anchored` | `python3 src/s4_analyze.py` |
| `\nLifeCtx` | 13,480 | results/summary.json | `dynamics.context.born_valid_lifetimes` | `python3 src/s4_analyze.py` |
| `\nBreaksCtx` | 274 | results/summary.json | `dynamics.context.breaks` | `python3 src/s4_analyze.py` |
| `\nExposureCtx` | 3,845 | results/summary.json | `dynamics.context.exposure_constraint_years` | `python3 src/s4_analyze.py` |
| `\nRateCtx` | 7.1 | results/summary.json | `dynamics.context.breaks_per_100_constraint_years` | `python3 src/s4_analyze.py` |
| `\nRateCICtx` | 5.1 to 9.8 | results/summary.json | `dynamics.context.rate_ci` | `python3 src/s4_analyze.py` |
| `\nRateScriptCtx` | 5.6 | results/summary.json | `dynamics.context.by_kind.script.rate_per_100cy` | `python3 src/s4_analyze.py` |
| `\nBreaksScriptCtx` | 18 | results/summary.json | `dynamics.context.by_kind.script.breaks` | `python3 src/s4_analyze.py` |
| `\nRateTargetCtx` | 1.4 | results/summary.json | `dynamics.context.by_kind.target.rate_per_100cy` | `python3 src/s4_analyze.py` |
| `\nBreaksTargetCtx` | 3 | results/summary.json | `dynamics.context.by_kind.target.breaks` | `python3 src/s4_analyze.py` |
| `\nRateManifestCtx` | 0.5 | results/summary.json | `dynamics.context.by_kind.manifest.rate_per_100cy` | `python3 src/s4_analyze.py` |
| `\nBreaksManifestCtx` | 1 | results/summary.json | `dynamics.context.by_kind.manifest.breaks` | `python3 src/s4_analyze.py` |
| `\nRateDepCtx` | 3.1 | results/summary.json | `dynamics.context.by_kind.dep.rate_per_100cy` | `python3 src/s4_analyze.py` |
| `\nBreaksDepCtx` | 2 | results/summary.json | `dynamics.context.by_kind.dep.breaks` | `python3 src/s4_analyze.py` |
| `\nEpisodesCtx` | 274 | results/summary.json | `repair.context.break_episodes` | `python3 src/s4_analyze.py` |
| `\nEpisodeReposCtx` | 95 | results/summary.json | `repair.context.repos` | `python3 src/s4_analyze.py` |
| `\nOpenCtx` | 123 | results/summary.json | `repair.context.ends.open` | `python3 src/s4_analyze.py` |
| `\nEditRepairCtx` | 128 | results/summary.json | `repair.context.ends.edit_repair` | `python3 src/s4_analyze.py` |
| `\nRepoRepairCtx` | 23 | results/summary.json | `repair.context.ends.repo_repair` | `python3 src/s4_analyze.py` |
| `\nShareOpenCtx` | 44.9 | results/summary.json | `repair.context.share_open_at_head` | `python3 src/s4_analyze.py` |
| `\nShareOpenCICtx` | 31.0 to 61.0 | results/summary.json | `repair.context.boot_ci_open_7_30_90_touched[0]` | `python3 src/s4_analyze.py` |
| `\nMedRepairCtx` | 78 | results/summary.json | `repair.context.km_median_days_to_repair` | `python3 src/s4_analyze.py` |
| `\nTouchedCtx` | 15.7 | results/summary.json | `repair.context.share_file_touched_in_break_commit` | `python3 src/s4_analyze.py` |
| `\nTouchedKCtx` | 43 | results/summary.json | `repair.context.file_touched_in_break_commit` | `python3 src/s4_analyze.py` |
| `\nInvalidationsCtx` | 610 | results/summary.json | `coupling.context.invalidations` | `python3 src/s4_analyze.py` |
| `\nSyncShareCtx` | 55.1 | results/summary.json | `coupling.context.in_sync_share` | `python3 src/s4_analyze.py` |
| `\nSyncShareCICtx` | 45.2 to 64.7 | results/summary.json | `coupling.context.ci` | `python3 src/s4_analyze.py` |
| `\nRemValidCtx` | 2,181 | results/summary.json | `coupling.context.removals_by_type.removal_valid` | `python3 src/s4_analyze.py` |
| `\nAnchRd` | 5,732 | results/summary.json | `head_drift.readme.born_valid_at_head` | `python3 src/s4_analyze.py` |
| `\nViolRd` | 46 | results/summary.json | `head_drift.readme.violated_at_head` | `python3 src/s4_analyze.py` |
| `\nDriftRd` | 0.80 | results/summary.json | `head_drift.readme.pooled_drift` | `python3 src/s4_analyze.py` |
| `\nDriftCIRd` | 0.50 to 1.15 | results/summary.json | `head_drift.readme.pooled_drift_ci` | `python3 src/s4_analyze.py` |
| `\nLifeRd` | 8,721 | results/summary.json | `dynamics.readme.born_valid_lifetimes` | `python3 src/s4_analyze.py` |
| `\nRateRd` | 8.4 | results/summary.json | `dynamics.readme.breaks_per_100_constraint_years` | `python3 src/s4_analyze.py` |
| `\nRateCIRd` | 5.5 to 11.4 | results/summary.json | `dynamics.readme.rate_ci` | `python3 src/s4_analyze.py` |
| `\nOpenRd` | 46 | results/summary.json | `repair.readme.ends.open` | `python3 src/s4_analyze.py` |
| `\nEditRepairRd` | 94 | results/summary.json | `repair.readme.ends.edit_repair` | `python3 src/s4_analyze.py` |
| `\nRepoRepairRd` | 28 | results/summary.json | `repair.readme.ends.repo_repair` | `python3 src/s4_analyze.py` |
| `\nShareOpenRd` | 27.4 | results/summary.json | `repair.readme.share_open_at_head` | `python3 src/s4_analyze.py` |
| `\nShareOpenCIRd` | 16.8 to 42.9 | results/summary.json | `repair.readme.boot_ci_open_7_30_90_touched[0]` | `python3 src/s4_analyze.py` |
| `\nMedRepairRd` | 8 | results/summary.json | `repair.readme.km_median_days_to_repair` | `python3 src/s4_analyze.py` |
| `\nInvalidationsRd` | 612 | results/summary.json | `coupling.readme.invalidations` | `python3 src/s4_analyze.py` |
| `\nSyncShareRd` | 72.5 | results/summary.json | `coupling.readme.in_sync_share` | `python3 src/s4_analyze.py` |
| `\nSyncShareCIRd` | 61.1 to 81.2 | results/summary.json | `coupling.readme.ci` | `python3 src/s4_analyze.py` |
| `\nRateRatio` | 0.85 | results/summary.json | `dynamics.rate_ratio_context_over_readme.estimate` | `python3 src/s4_analyze.py` |
| `\nRateRatioCI` | 0.59 to 1.20 | results/summary.json | `dynamics.rate_ratio_context_over_readme.ci` | `python3 src/s4_analyze.py` |
| `\nDiffOpen` | 17.5 | results/summary.json | `paired_diff_context_minus_readme.share_open.diff` | `python3 src/s4_analyze.py` |
| `\nDiffOpenCI` | 2.4 to 33.2 | results/summary.json | `paired_diff_context_minus_readme.share_open.ci` | `python3 src/s4_analyze.py` |
| `\nDiffDrift` | 0.32 | results/summary.json | `paired_diff_context_minus_readme.pooled_drift.diff` | `python3 src/s4_analyze.py` |
| `\nDiffDriftCI` | -0.15 to 0.81 | results/summary.json | `paired_diff_context_minus_readme.pooled_drift.ci` | `python3 src/s4_analyze.py` |
| `\nTopTenShare` | 40.1 | results/summary.json | `concentration.top10_repos_share_of_breaks` | `python3 src/s4_analyze.py` |
| `\nMaxBreaksRepo` | 30 | results/summary.json | `concentration.max_breaks_one_repo` | `python3 src/s4_analyze.py` |
| `\nBreakCommits` | 155 | results/summary.json | `who_breaks.breaking_commits` | `python3 src/s4_analyze.py` |
| `\nBreakAgentShare` | 18.7 | results/summary.json | `who_breaks.share` | `python3 src/s4_analyze.py` |
| `\nBaseAgentShare` | 20.2 | results/summary.json | `who_breaks.base_share` | `python3 src/s4_analyze.py` |
| `\nNaiveFlagged` | 1,581 | results/summary.json | `baselines.single_snapshot_flagged` | `python3 src/s4_analyze.py` |
| `\nNaiveRate` | 12.7 | results/summary.json | `baselines.single_snapshot_rate` | `python3 src/s4_analyze.py` |
| `\nNaiveAnchoredShare` | 7.8 | results/summary.json | `baselines.share_of_single_snapshot_flags_that_are_anchored` | `python3 src/s4_analyze.py` |
| `\nTwoSnap` | 75 | results/summary.json | `baselines.two_snapshot_flagged` | `python3 src/s4_analyze.py` |
| `\nTwoSnapRecall` | 61.0 | results/summary.json | `baselines.two_snapshot_recall_of_anchored_head` | `python3 src/s4_analyze.py` |
| `\nInvisibleBreaks` | 55.1 | results/summary.json | `baselines.share_breaks_invisible_at_head` | `python3 src/s4_analyze.py` |
| `\nAgeDriftThirty` | 0.46 | results/drift_by_age_summary.csv | `age_days=30.mean_drift` | `python3 src/s6_figures.py` |
| `\nAgeDriftCIThirty` | 0.28 to 0.65 | results/drift_by_age_summary.csv | `age_days=30.lo,hi` | `python3 src/s6_figures.py` |
| `\nAgeDriftNinety` | 0.70 | results/drift_by_age_summary.csv | `age_days=90.mean_drift` | `python3 src/s6_figures.py` |
| `\nAgeDriftOneEighty` | 1.43 | results/drift_by_age_summary.csv | `age_days=180.mean_drift` | `python3 src/s6_figures.py` |
| `\nAgeDriftTwoForty` | 2.42 | results/drift_by_age_summary.csv | `age_days=240.mean_drift` | `python3 src/s6_figures.py` |
| `\nAgeDriftCITwoForty` | 1.33 to 3.70 | results/drift_by_age_summary.csv | `age_days=240.lo,hi` | `python3 src/s6_figures.py` |
| `\nValAN` | 100 | results/validation_summary.json | `extraction.n` | `python3 src/s7_validation_summary.py` |
| `\nValAK` | 96 | results/validation_summary.json | `extraction.genuine` | `python3 src/s7_validation_summary.py` |
| `\nValBN` | 60 | results/validation_summary.json | `breaks.n` | `python3 src/s7_validation_summary.py` |
| `\nValBK` | 51 | results/validation_summary.json | `breaks.true_staleness` | `python3 src/s7_validation_summary.py` |
| `\nLlmKappaA` | 0.14 | results/llm_second_rater_summary.json | `A.cohen_kappa` | `python3 src/s8_llm_second_rater.py` |
| `\nOvVersions` | 9 | results/overview_example.json | `n_versions` | `python3 src/s6_figures.py` |
| `\nOvAge` | 415 | results/overview_example.json | `age_days` | `python3 src/s6_figures.py` |
| `\nInvRateCtx` | 15.9 | results/robustness.json | `invalidation.context_invalidation_rate.est` | `python3 src/s4b_robustness.py` |
| `\nInvRateCtxCI` | 12.2 to 19.9 | results/robustness.json | `invalidation.context_invalidation_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncRateCtx` | 8.7 | results/robustness.json | `invalidation.context_insync_rate.est` | `python3 src/s4b_robustness.py` |
| `\nSyncRateCtxCI` | 6.1 to 11.9 | results/robustness.json | `invalidation.context_insync_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nAnchSyncCtx` | 336 | results/robustness.json | `invalidation.counts.context.in_sync` | `python3 src/s4b_robustness.py` |
| `\nInvRateRd` | 30.5 | results/robustness.json | `invalidation.readme_invalidation_rate.est` | `python3 src/s4b_robustness.py` |
| `\nInvRateRdCI` | 21.8 to 41.6 | results/robustness.json | `invalidation.readme_invalidation_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncRateRd` | 22.2 | results/robustness.json | `invalidation.readme_insync_rate.est` | `python3 src/s4b_robustness.py` |
| `\nSyncRateRdCI` | 14.2 to 32.2 | results/robustness.json | `invalidation.readme_insync_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nInvRatio` | 0.52 | results/robustness.json | `invalidation.invalidation_ratio_ctx_over_readme.est` | `python3 src/s4b_robustness.py` |
| `\nInvRatioCI` | 0.37 to 0.75 | results/robustness.json | `invalidation.invalidation_ratio_ctx_over_readme.ci` | `python3 src/s4b_robustness.py` |
| `\nInvRatioEntry` | 0.33 | results/robustness.json | `invalidation_entry_observed.invalidation_ratio_ctx_over_readme.est` | `python3 src/s4b_robustness.py` |
| `\nInvRatioEntryCI` | 0.22 to 0.50 | results/robustness.json | `invalidation_entry_observed.invalidation_ratio_ctx_over_readme.ci` | `python3 src/s4b_robustness.py` |
| `\nInvRateRdEntry` | 48.3 | results/robustness.json | `invalidation_entry_observed.readme_invalidation_rate.est` | `python3 src/s4b_robustness.py` |
| `\nInvRateRdEntryCI` | 33.3 to 68.6 | results/robustness.json | `invalidation_entry_observed.readme_invalidation_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nBreakRatioEntry` | 0.61 | results/robustness.json | `invalidation_entry_observed.break_ratio_ctx_over_readme.est` | `python3 src/s4b_robustness.py` |
| `\nBreakRatioEntryCI` | 0.42 to 0.95 | results/robustness.json | `invalidation_entry_observed.break_ratio_ctx_over_readme.ci` | `python3 src/s4b_robustness.py` |
| `\nInvRatioPaths` | 0.48 | results/robustness.json | `invalidation_paths_only.invalidation_ratio_ctx_over_readme.est` | `python3 src/s4b_robustness.py` |
| `\nShareRdTrunc` | 46 | results/robustness.json | `invalidation.share_readme_left_truncated` | `python3 src/s4b_robustness.py` |
| `\nCifInvYearCtx` | 7.0 | results/robustness.json | `cif.context_invalidated_365.est` | `python3 src/s4b_robustness.py` |
| `\nCifInvYearRd` | 13.3 | results/robustness.json | `cif.readme_entry_observed_invalidated_365.est` | `python3 src/s4b_robustness.py` |
| `\nSyncDiff` | 17.5 | results/robustness.json | `insync.event_level.diff.est (sign flipped)` | `python3 src/s4b_robustness.py` |
| `\nSyncDiffCI` | 5.3 to 27.9 | results/robustness.json | `insync.event_level.diff.ci (sign flipped)` | `python3 src/s4b_robustness.py` |
| `\nSyncCommitCtx` | 43.2 | results/robustness.json | `insync.commit_level.context.est` | `python3 src/s4b_robustness.py` |
| `\nSyncCommitRd` | 59.0 | results/robustness.json | `insync.commit_level.readme.est` | `python3 src/s4b_robustness.py` |
| `\nSyncCommitDiff` | 15.8 | results/robustness.json | `insync.commit_level.diff.est (sign flipped)` | `python3 src/s4b_robustness.py` |
| `\nSyncCommitDiffCI` | 5.8 to 26.2 | results/robustness.json | `insync.commit_level.diff.ci (sign flipped)` | `python3 src/s4b_robustness.py` |
| `\nSyncDayCtx` | 67.0 | results/robustness.json | `insync.quick_repair_one_day_as_in_sync.context.est` | `python3 src/s4b_robustness.py` |
| `\nSyncDayRd` | 83.0 | results/robustness.json | `insync.quick_repair_one_day_as_in_sync.readme.est` | `python3 src/s4b_robustness.py` |
| `\nSyncDayDiff` | 16.0 | results/robustness.json | `insync.quick_repair_one_day_as_in_sync.diff.est (sign flipped)` | `python3 src/s4b_robustness.py` |
| `\nSyncDayDiffCI` | 5.8 to 25.5 | results/robustness.json | `insync.quick_repair_one_day_as_in_sync.diff.ci (sign flipped)` | `python3 src/s4b_robustness.py` |
| `\nInvCommitsCtx` | 273 | results/robustness.json | `insync.commit_level.context_commits.est` | `python3 src/s4b_robustness.py` |
| `\nInvCommitsRd` | 249 | results/robustness.json | `insync.commit_level.readme_commits.est` | `python3 src/s4b_robustness.py` |
| `\nSyncRepoMeanCtx` | 48.9 | results/robustness.json | `insync.insync_repo_mean.context` | `python3 src/s4b_robustness.py` |
| `\nOpenOldCtx` | 42.6 | results/robustness.json | `open.breaks_older_than_30_days.context.est` | `python3 src/s4b_robustness.py` |
| `\nSyncRepoMeanRd` | 65.3 | results/robustness.json | `insync.insync_repo_mean.readme` | `python3 src/s4b_robustness.py` |
| `\nOpenOldRd` | 19.4 | results/robustness.json | `open.breaks_older_than_30_days.readme.est` | `python3 src/s4b_robustness.py` |
| `\nOpenOldDiff` | 23.2 | results/robustness.json | `open.breaks_older_than_30_days.diff.est` | `python3 src/s4b_robustness.py` |
| `\nOpenOldDiffCI` | 7.3 to 40.7 | results/robustness.json | `open.breaks_older_than_30_days.diff.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncBothRepos` | 70 | results/robustness.json | `insync.insync_both_sides.repos` | `python3 src/s4b_robustness.py` |
| `\nSyncLooRange` | 14.9 to 19.8 | results/robustness.json | `insync.insync_leave_one_out.min,max` | `python3 src/s4b_robustness.py` |
| `\nSyncTrimFive` | 11.6 | results/robustness.json | `insync.insync_trimmed_top5_each_side.diff` | `python3 src/s4b_robustness.py` |
| `\nSyncTrimFiveCI` | -0.9 to 23.1 | results/robustness.json | `insync.insync_trimmed_top5_each_side.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncTrimFiveCtx` | 56.5 | results/robustness.json | `insync.insync_trimmed_top5_each_side.context` | `python3 src/s4b_robustness.py` |
| `\nSyncTrimFiveRd` | 68.1 | results/robustness.json | `insync.insync_trimmed_top5_each_side.readme` | `python3 src/s4b_robustness.py` |
| `\nOpenBothRepos` | 36 | results/robustness.json | `open.both_sides.repos` | `python3 src/s4b_robustness.py` |
| `\nOpenTrimFive` | 7.5 | results/robustness.json | `open.trimmed_top5_each_side.diff` | `python3 src/s4b_robustness.py` |
| `\nOpenTrimFiveCI` | -10.1 to 23.8 | results/robustness.json | `open.trimmed_top5_each_side.ci` | `python3 src/s4b_robustness.py` |
| `\nOpenTrimFiveCtx` | 55.9 | results/robustness.json | `open.trimmed_top5_each_side.context` | `python3 src/s4b_robustness.py` |
| `\nOpenTrimFiveRd` | 48.4 | results/robustness.json | `open.trimmed_top5_each_side.readme` | `python3 src/s4b_robustness.py` |
| `\nRdTopTwoShare` | 23 | results/robustness.json | `insync.insync_concentration.readme_top2_share_of_events` | `python3 src/s4b_robustness.py` |
| `\nRewrittenK` | 20 | results/robustness.json | `repair_mode.rewritten_to_valid_target` | `python3 src/s4b_robustness.py` |
| `\nDeletedK` | 96 | results/robustness.json | `repair_mode.deleted` | `python3 src/s4b_robustness.py` |
| `\nRepairClassified` | 116 | results/robustness.json | `repair_mode.classified` | `python3 src/s4b_robustness.py` |
| `\nRewrittenShare` | 17 | results/robustness.json | `repair_mode.rewritten_share` | `python3 src/s4b_robustness.py` |
| `\nDriftSlashedCtx` | 1.47 | results/robustness.json | `drift_sens.context.slashed_paths.drift` | `python3 src/s4b_robustness.py` |
| `\nRateSlashedCtx` | 10.1 | results/robustness.json | `drift_sens.context.slashed_paths.rate_per_100cy` | `python3 src/s4b_robustness.py` |
| `\nDriftBareCtx` | 1.08 | results/robustness.json | `drift_sens.context.bare_names.drift` | `python3 src/s4b_robustness.py` |
| `\nRateBareCtx` | 6.0 | results/robustness.json | `drift_sens.context.bare_names.rate_per_100cy` | `python3 src/s4b_robustness.py` |
| `\nBreaksBareCtx` | 82 | results/robustness.json | `drift_sens.context.bare_names.breaks` | `python3 src/s4b_robustness.py` |
| `\nDriftNonPathCtx` | 0.37 | results/robustness.json | `drift_sens.context.non_path.drift` | `python3 src/s4b_robustness.py` |
| `\nRateNonPathCtx` | 2.9 | results/robustness.json | `drift_sens.context.non_path.rate_per_100cy` | `python3 src/s4b_robustness.py` |
| `\nAnchNonPathCtx` | 2,155 | results/robustness.json | `drift_sens.context.non_path.anchored_at_head` | `python3 src/s4b_robustness.py` |
| `\nViolNonPathCtx` | 8 | results/robustness.json | `drift_sens.context.non_path.violated` | `python3 src/s4b_robustness.py` |
| `\nBreaksNonPathCtx` | 24 | results/robustness.json | `drift_sens.context.non_path.breaks` | `python3 src/s4b_robustness.py` |
| `\nDriftDirCtx` | 1.51 | results/robustness.json | `drift_sens.context.directory_paths.drift` | `python3 src/s4b_robustness.py` |
| `\nDriftFilePathCtx` | 1.24 | results/robustness.json | `drift_sens.context.file_paths.drift` | `python3 src/s4b_robustness.py` |
| `\nShareBareCtx` | 42 | results/robustness.json | `drift_sens.context.share_bare_among_head_paths` | `python3 src/s4b_robustness.py` |
| `\nShareLenientBirthCtx` | 21 | results/robustness.json | `drift_sens.context.share_lenient_only_at_birth` | `python3 src/s4b_robustness.py` |
| `\nHiddenCtx` | 40 | results/robustness.json | `lenient.context.exact_path_gone_but_lenient_match` | `python3 src/s4b_robustness.py` |
| `\nHiddenBaseCtx` | 84 | results/robustness.json | `lenient.context.violated_lenient` | `python3 src/s4b_robustness.py` |
| `\nStrictPathsCtx` | 6,448 | results/robustness.json | `lenient.context.strictly_anchored_paths_at_head` | `python3 src/s4b_robustness.py` |
| `\nLenientDriftCtx` | 1.30 | results/robustness.json | `lenient.context.drift_lenient` | `python3 src/s4b_robustness.py` |
| `\nUpperDriftCtx` | 1.92 | results/robustness.json | `lenient.context.drift_if_all_hidden_are_real` | `python3 src/s4b_robustness.py` |
| `\nEnumDriftCtx` | 0.80 | results/robustness.json | `enumerated.context.drift` | `python3 src/s4b_robustness.py` |
| `\nEnumRateCtx` | 5.3 | results/robustness.json | `enumerated.context.break_rate` | `python3 src/s4b_robustness.py` |
| `\nEnumInvRateCtx` | 13.5 | results/robustness.json | `enumerated.context.invalidation_rate` | `python3 src/s4b_robustness.py` |
| `\nEnumSyncCtx` | 60.9 | results/robustness.json | `enumerated.context.insync_share` | `python3 src/s4b_robustness.py` |
| `\nEnumOpenCtx` | 52.2 | results/robustness.json | `enumerated.context.open_share` | `python3 src/s4b_robustness.py` |
| `\nHitAllCtx` | 9.3 | results/robustness.json | `denominators.context.share_of_all_files` | `python3 src/s4b_robustness.py` |
| `\nHitKCtx` | 70 | results/robustness.json | `denominators.context.files_hit` | `python3 src/s4b_robustness.py` |
| `\nHitDenCtx` | 645 | results/robustness.json | `denominators.context.files_with_anchored` | `python3 src/s4b_robustness.py` |
| `\nRateSlashedRd` | 12.2 | results/robustness.json | `drift_sens.readme.slashed_paths.rate_per_100cy` | `python3 src/s4b_robustness.py` |
| `\nRateBareRd` | 6.9 | results/robustness.json | `drift_sens.readme.bare_names.rate_per_100cy` | `python3 src/s4b_robustness.py` |
| `\nRateNonPathRd` | 1.9 | results/robustness.json | `drift_sens.readme.non_path.rate_per_100cy` | `python3 src/s4b_robustness.py` |
| `\nEnumDriftRd` | 0.69 | results/robustness.json | `enumerated.readme.drift` | `python3 src/s4b_robustness.py` |
| `\nEnumRateRd` | 6.5 | results/robustness.json | `enumerated.readme.break_rate` | `python3 src/s4b_robustness.py` |
| `\nEnumInvRateRd` | 26.8 | results/robustness.json | `enumerated.readme.invalidation_rate` | `python3 src/s4b_robustness.py` |
| `\nEnumSyncRd` | 75.8 | results/robustness.json | `enumerated.readme.insync_share` | `python3 src/s4b_robustness.py` |
| `\nEnumOpenRd` | 37.0 | results/robustness.json | `enumerated.readme.open_share` | `python3 src/s4b_robustness.py` |
| `\nHitAllRd` | 5.7 | results/robustness.json | `denominators.readme.share_of_all_files` | `python3 src/s4b_robustness.py` |
| `\nHitKRd` | 30 | results/robustness.json | `denominators.readme.files_hit` | `python3 src/s4b_robustness.py` |
| `\nHitDenRd` | 465 | results/robustness.json | `denominators.readme.files_with_anchored` | `python3 src/s4b_robustness.py` |
| `\nHitAllCICtx` | 7.4 to 11.6 | results/robustness.json | `denominators.context.wilson_all` | `python3 src/s4b_robustness.py` |
| `\nHitAllAgents` | 8.7 | results/robustness.json | `denominators.AGENTS.md.share_of_all_files` | `python3 src/s4b_robustness.py` |
| `\nHitDenAgents` | 274 | results/robustness.json | `denominators.AGENTS.md.files_with_anchored` | `python3 src/s4b_robustness.py` |
| `\nHitKAgents` | 25 | results/robustness.json | `denominators.AGENTS.md.files_hit` | `python3 src/s4b_robustness.py` |
| `\nHitAllClaude` | 11.1 | results/robustness.json | `denominators.CLAUDE.md.share_of_all_files` | `python3 src/s4b_robustness.py` |
| `\nHitDenClaude` | 245 | results/robustness.json | `denominators.CLAUDE.md.files_with_anchored` | `python3 src/s4b_robustness.py` |
| `\nHitKClaude` | 32 | results/robustness.json | `denominators.CLAUDE.md.files_hit` | `python3 src/s4b_robustness.py` |
| `\nHitAllCursor` | 6.7 | results/robustness.json | `denominators..cursorrules.share_of_all_files` | `python3 src/s4b_robustness.py` |
| `\nHitDenCursor` | 85 | results/robustness.json | `denominators..cursorrules.files_with_anchored` | `python3 src/s4b_robustness.py` |
| `\nHitKCursor` | 9 | results/robustness.json | `denominators..cursorrules.files_hit` | `python3 src/s4b_robustness.py` |
| `\nHitAllCopilot` | 8.9 | results/robustness.json | `denominators.copilot-instructions.md.share_of_all_files` | `python3 src/s4b_robustness.py` |
| `\nHitDenCopilot` | 41 | results/robustness.json | `denominators.copilot-instructions.md.files_with_anchored` | `python3 src/s4b_robustness.py` |
| `\nHitKCopilot` | 4 | results/robustness.json | `denominators.copilot-instructions.md.files_hit` | `python3 src/s4b_robustness.py` |
| `\nEnumRepos` | 430 | results/robustness.json | `enumerated.repos` | `python3 src/s4b_robustness.py` |
| `\nNSampledRepos` | 112 | results/robustness.json | `corpus.repos minus enumerated.repos` | `python3 src/s4b_robustness.py` |
| `\nAgeFilesDriftTwoForty` | 21 | results/robustness.json | `age.all_files[240].files_with_drift` | `python3 src/s4b_robustness.py` |
| `\nAgeFilesTwoFortyAll` | 124 | results/robustness.json | `age.all_files[240].files` | `python3 src/s4b_robustness.py` |
| `\nCohortThirty` | 0.39 | results/robustness.json | `age.cohort_240[30].mean_drift` | `python3 src/s4b_robustness.py` |
| `\nCohortNinety` | 0.87 | results/robustness.json | `age.cohort_240[90].mean_drift` | `python3 src/s4b_robustness.py` |
| `\nCohortOneEighty` | 2.42 | results/robustness.json | `age.cohort_240[180].mean_drift` | `python3 src/s4b_robustness.py` |
| `\nCohortTwoForty` | 2.42 | results/robustness.json | `age.cohort_240[240].mean_drift` | `python3 src/s4b_robustness.py` |
| `\nKitA` | 190 | labelling/kit_summary.json | `sum of A_*.sampled` | `python3 src/s10_labelling_kit.py` |
| `\nKitAViol` | 60 | labelling/kit_summary.json | `A_anchored_violated.sampled` | `python3 src/s10_labelling_kit.py` |
| `\nKitBCtx` | 79 | labelling/kit_summary.json | `B_context_*.sampled` | `python3 src/s10_labelling_kit.py` |
| `\nKitBRd` | 61 | labelling/kit_summary.json | `B_readme_*.sampled` | `python3 src/s10_labelling_kit.py` |
| `\nKitS` | 60 | labelling/kit_summary.json | `S_context.sampled (same for README)` | `python3 src/s10_labelling_kit.py` |
| `\nKitRFiles` | 30 | labelling/kit_summary.json | `R.files` | `python3 src/s10_labelling_kit.py` |
| `\nKitRLines` | 590 | labelling/kit_summary.json | `R.lines` | `python3 src/s10_labelling_kit.py` |
| `\nKitL` | 100 | labelling/kit_summary.json | `L.sampled` | `python3 src/s10_labelling_kit.py` |
| `\nKitCalib` | 20 | labelling/kit_summary.json | `calibration_items` | `python3 src/s10_labelling_kit.py` |
| `\nRateRdEntry` | 11.8 | results/robustness.json | `invalidation_entry_observed.readme_break_rate.est` | `python3 src/s4b_robustness.py` |
| `\nRateRdEntryCI` | 7.3 to 16.7 | results/robustness.json | `invalidation_entry_observed.readme_break_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nBreakRatioPaths` | 0.80 | results/robustness.json | `invalidation_paths_only.break_ratio_ctx_over_readme.est` | `python3 src/s4b_robustness.py` |
| `\nBreakRatioPathsCI` | 0.57 to 1.19 | results/robustness.json | `invalidation_paths_only.break_ratio_ctx_over_readme.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncRateRdEntry` | 36.6 | results/robustness.json | `invalidation_entry_observed.readme_insync_rate.est` | `python3 src/s4b_robustness.py` |
| `\nSyncRateRdEntryCI` | 21.0 to 57.2 | results/robustness.json | `invalidation_entry_observed.readme_insync_rate.ci` | `python3 src/s4b_robustness.py` |
| `\nLifeRdEntry` | 4,736 | results/robustness.json | `cif.n.readme_entry_observed` | `python3 src/s4b_robustness.py` |
| `\nBreakRatioSpan` | 0.64 | results/robustness.json | `form.rates_code_span.break_ratio.est` | `python3 src/s4b_robustness.py` |
| `\nBreakRatioSpanCI` | 0.43 to 0.96 | results/robustness.json | `form.rates_code_span.break_ratio.ci` | `python3 src/s4b_robustness.py` |
| `\nInvRatioSpan` | 0.50 | results/robustness.json | `form.rates_code_span.invalidation_ratio.est` | `python3 src/s4b_robustness.py` |
| `\nInvRatioSpanCI` | 0.34 to 0.76 | results/robustness.json | `form.rates_code_span.invalidation_ratio.ci` | `python3 src/s4b_robustness.py` |
| `\nCompLinkCtx` | 5 | results/robustness.json | `form.composition_anchored.context.link` | `python3 src/s4b_robustness.py` |
| `\nSyncFormLinkCtx` | 55.2 | results/robustness.json | `form.insync_by_form.strata.link.context_share` | `python3 src/s4b_robustness.py` |
| `\nOpenFormLinkCtx` | 15.4 | results/robustness.json | `form.open_by_form.strata.link.context_share` | `python3 src/s4b_robustness.py` |
| `\nCompSpanCtx` | 77 | results/robustness.json | `form.composition_anchored.context.code_span` | `python3 src/s4b_robustness.py` |
| `\nSyncFormSpanCtx` | 54.3 | results/robustness.json | `form.insync_by_form.strata.code_span.context_share` | `python3 src/s4b_robustness.py` |
| `\nSyncFormNSpanCtx` | 519 | results/robustness.json | `form.insync_by_form.strata.code_span.context_n` | `python3 src/s4b_robustness.py` |
| `\nOpenFormSpanCtx` | 47.7 | results/robustness.json | `form.open_by_form.strata.code_span.context_share` | `python3 src/s4b_robustness.py` |
| `\nSyncFormCmdCtx` | 61.3 | results/robustness.json | `form.insync_by_form.strata.command.context_share` | `python3 src/s4b_robustness.py` |
| `\nCompDocCtx` | 19 | results/robustness.json | `form.composition_target.context.doc_file` | `python3 src/s4b_robustness.py` |
| `\nBulkShareCtx` | 25 | results/robustness.json | `bulk_rewrites.context.share_bulk` | `python3 src/s4b_robustness.py` |
| `\nSyncNoBulkCtx` | 47.8 | results/robustness.json | `bulk_rewrites.context.insync_share_without_bulk` | `python3 src/s4b_robustness.py` |
| `\nReaddedCtx` | 84 | results/robustness.json | `readded_keys.context.of_which_key_live_at_head` | `python3 src/s4b_robustness.py` |
| `\nCompLinkRd` | 54 | results/robustness.json | `form.composition_anchored.readme.link` | `python3 src/s4b_robustness.py` |
| `\nSyncFormLinkRd` | 76.9 | results/robustness.json | `form.insync_by_form.strata.link.readme_share` | `python3 src/s4b_robustness.py` |
| `\nSyncFormNLinkRd` | 390 | results/robustness.json | `form.insync_by_form.strata.link.readme_n` | `python3 src/s4b_robustness.py` |
| `\nOpenFormLinkRd` | 11.1 | results/robustness.json | `form.open_by_form.strata.link.readme_share` | `python3 src/s4b_robustness.py` |
| `\nOpenFormNLinkRd` | 90 | results/robustness.json | `form.open_by_form.strata.link.readme_n` | `python3 src/s4b_robustness.py` |
| `\nCompSpanRd` | 29 | results/robustness.json | `form.composition_anchored.readme.code_span` | `python3 src/s4b_robustness.py` |
| `\nSyncFormSpanRd` | 64.1 | results/robustness.json | `form.insync_by_form.strata.code_span.readme_share` | `python3 src/s4b_robustness.py` |
| `\nOpenFormSpanRd` | 44.9 | results/robustness.json | `form.open_by_form.strata.code_span.readme_share` | `python3 src/s4b_robustness.py` |
| `\nSyncFormCmdRd` | 70.0 | results/robustness.json | `form.insync_by_form.strata.command.readme_share` | `python3 src/s4b_robustness.py` |
| `\nCompDocRd` | 43 | results/robustness.json | `form.composition_target.readme.doc_file` | `python3 src/s4b_robustness.py` |
| `\nBulkShareRd` | 43 | results/robustness.json | `bulk_rewrites.readme.share_bulk` | `python3 src/s4b_robustness.py` |
| `\nSyncNoBulkRd` | 60.3 | results/robustness.json | `bulk_rewrites.readme.insync_share_without_bulk` | `python3 src/s4b_robustness.py` |
| `\nReaddedRd` | 586 | results/robustness.json | `readded_keys.readme.of_which_key_live_at_head` | `python3 src/s4b_robustness.py` |
| `\nSyncFormDiffLink` | 21.8 | results/robustness.json | `form.insync_by_form.strata.link.diff` | `python3 src/s4b_robustness.py` |
| `\nOpenFormDiffLink` | 4.3 | results/robustness.json | `form.open_by_form.strata.link.diff` | `python3 src/s4b_robustness.py` |
| `\nSyncFormDiffSpan` | 9.7 | results/robustness.json | `form.insync_by_form.strata.code_span.diff` | `python3 src/s4b_robustness.py` |
| `\nOpenFormDiffSpan` | 2.8 | results/robustness.json | `form.open_by_form.strata.code_span.diff` | `python3 src/s4b_robustness.py` |
| `\nSyncFormDiffCmd` | 8.7 | results/robustness.json | `form.insync_by_form.strata.command.diff` | `python3 src/s4b_robustness.py` |
| `\nSyncFormDiffSpanCI` | -6.7 to 23.5 | results/robustness.json | `form.insync_by_form.strata.code_span.diff_ci` | `python3 src/s4b_robustness.py` |
| `\nOpenFormDiffSpanCI` | -16.0 to 23.0 | results/robustness.json | `form.open_by_form.strata.code_span.diff_ci` | `python3 src/s4b_robustness.py` |
| `\nSyncStratForm` | 11.3 | results/robustness.json | `form.insync_by_form.stratified_diff.est` | `python3 src/s4b_robustness.py` |
| `\nSyncStratFormCI` | -4.3 to 23.8 | results/robustness.json | `form.insync_by_form.stratified_diff.ci` | `python3 src/s4b_robustness.py` |
| `\nOpenStratForm` | 0.7 | results/robustness.json | `form.open_by_form.stratified_diff.est` | `python3 src/s4b_robustness.py` |
| `\nOpenStratFormCI` | -15.8 to 19.1 | results/robustness.json | `form.open_by_form.stratified_diff.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncStratTarget` | 17.8 | results/robustness.json | `form.insync_by_target.stratified_diff.est` | `python3 src/s4b_robustness.py` |
| `\nSyncStratTargetCI` | 4.1 to 29.1 | results/robustness.json | `form.insync_by_target.stratified_diff.ci` | `python3 src/s4b_robustness.py` |
| `\nOpenStratTarget` | 13.7 | results/robustness.json | `form.open_by_target.stratified_diff.est` | `python3 src/s4b_robustness.py` |
| `\nOpenStratTargetCI` | -4.5 to 30.7 | results/robustness.json | `form.open_by_target.stratified_diff.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncNoDocLinks` | 19.6 | results/robustness.json | `form.without_links_to_doc_files.insync_diff.est` | `python3 src/s4b_robustness.py` |
| `\nSyncNoDocLinksCI` | 6.4 to 31.2 | results/robustness.json | `form.without_links_to_doc_files.insync_diff.ci` | `python3 src/s4b_robustness.py` |
| `\nOpenNoDocLinks` | 3.8 | results/robustness.json | `form.without_links_to_doc_files.open_diff.est` | `python3 src/s4b_robustness.py` |
| `\nOpenNoDocLinksCI` | -13.9 to 22.7 | results/robustness.json | `form.without_links_to_doc_files.open_diff.ci` | `python3 src/s4b_robustness.py` |
| `\nSyncNoBulkDiff` | 12.5 | results/robustness.json | `bulk_rewrites.diff_without_bulk` | `python3 src/s4b_robustness.py` |
| `\nSyncNoBulkDiffCI` | 0.5 to 24.0 | results/robustness.json | `bulk_rewrites.diff_without_bulk_ci` | `python3 src/s4b_robustness.py` |
| `\nSyncSignFor` | 33 | results/robustness.json | `within_repo.insync.favours_headline_direction` | `python3 src/s4b_robustness.py` |
| `\nSyncSignAgainst` | 13 | results/robustness.json | `within_repo.insync.opposite` | `python3 src/s4b_robustness.py` |
| `\nSyncSignTies` | 24 | results/robustness.json | `within_repo.insync.ties` | `python3 src/s4b_robustness.py` |
| `\nSyncSignP` | 0.005 | results/robustness.json | `within_repo.insync.sign_test_p` | `python3 src/s4b_robustness.py` |
| `\nOpenSignFor` | 15 | results/robustness.json | `within_repo.open.favours_headline_direction` | `python3 src/s4b_robustness.py` |
| `\nOpenSignAgainst` | 4 | results/robustness.json | `within_repo.open.opposite` | `python3 src/s4b_robustness.py` |
| `\nOpenSignTies` | 17 | results/robustness.json | `within_repo.open.ties` | `python3 src/s4b_robustness.py` |
| `\nOpenSignP` | 0.019 | results/robustness.json | `within_repo.open.sign_test_p` | `python3 src/s4b_robustness.py` |
| `\nCifBreakHalfYearCtx` | 2.6 | results/robustness.json | `cif.context_break_180.est` | `python3 src/s4b_robustness.py` |
| `\nCifBreakHalfYearCtxCI` | 1.9 to 3.4 | results/robustness.json | `cif.context_break_180.ci` | `python3 src/s4b_robustness.py` |
| `\nCifSyncHalfYearCtx` | 3.3 | results/robustness.json | `cif.context_sync_removal_180.est` | `python3 src/s4b_robustness.py` |
| `\nCifRemValidHalfYearCtx` | 20.5 | results/robustness.json | `cif.context_removal_valid_180.est` | `python3 src/s4b_robustness.py` |
| `\nAtRiskHalfYearCtx` | 2,889 | results/robustness.json | `at_risk.context.180.at_risk` | `python3 src/s4b_robustness.py` |
| `\nAtRiskYearCtx` | 260 | results/robustness.json | `at_risk.context.365.at_risk` | `python3 src/s4b_robustness.py` |
| `\nAtRiskFilesYearCtx` | 31 | results/robustness.json | `at_risk.context.365.files` | `python3 src/s4b_robustness.py` |
| `\nMedFollowCtx` | 76 | results/robustness.json | `at_risk.context.median_followup_days` | `python3 src/s4b_robustness.py` |
| `\nCifBreakHalfYearRd` | 3.1 | results/robustness.json | `cif.readme_entry_observed_break_180.est` | `python3 src/s4b_robustness.py` |
| `\nCifBreakHalfYearRdCI` | 1.9 to 4.6 | results/robustness.json | `cif.readme_entry_observed_break_180.ci` | `python3 src/s4b_robustness.py` |
| `\nCifSyncHalfYearRd` | 8.1 | results/robustness.json | `cif.readme_entry_observed_sync_removal_180.est` | `python3 src/s4b_robustness.py` |
| `\nCifRemValidHalfYearRd` | 38.8 | results/robustness.json | `cif.readme_entry_observed_removal_valid_180.est` | `python3 src/s4b_robustness.py` |
| `\nAtRiskHalfYearRd` | 539 | results/robustness.json | `at_risk.readme_entry_observed.180.at_risk` | `python3 src/s4b_robustness.py` |
| `\nAtRiskYearRd` | 40 | results/robustness.json | `at_risk.readme_entry_observed.365.at_risk` | `python3 src/s4b_robustness.py` |
| `\nAtRiskFilesYearRd` | 13 | results/robustness.json | `at_risk.readme_entry_observed.365.files` | `python3 src/s4b_robustness.py` |
| `\nMedFollowRd` | 42 | results/robustness.json | `at_risk.readme_entry_observed.median_followup_days` | `python3 src/s4b_robustness.py` |
| `\nEnteredInvalid` | 123 | results/robustness.json | `head_partition.entered_invalid_later_valid` | `python3 src/s4b_robustness.py` |
| `\nLifeNotAnch` | 2,140 | results/robustness.json | `head_partition.lifetimes_not_anchored` | `python3 src/s4b_robustness.py` |
| `\nOvBreaks` | 9 | results/overview_example.json | `break_episodes` | `python3 src/s6_figures.py` |
| `\nOvRows` | 14 | results/overview_example.json | `rows_shown` | `python3 src/s6_figures.py` |
| `\nOvFirstBreakDays` | 17 | results/overview_example.json | `first_break_days_after_creation` | `python3 src/s6_figures.py` |
| `\nOvOpen` | 0 | results/overview_example.json | `open_at_head` | `python3 src/s6_figures.py` |
| `\nOvMinStay` | 62 | results/overview_example.json | `min_days_in_file_after_break` | `python3 src/s6_figures.py` |
| `\nOvMaxStay` | 96 | results/overview_example.json | `max_days_in_file_after_break` | `python3 src/s6_figures.py` |
| `\nOvMarchBreaks` | 3 | results/overview_example.json | `breaks_by_day (March 2026)` | `python3 src/s6_figures.py` |
| `\nOvAprilBreaks` | 5 | results/overview_example.json | `breaks_by_day (April 2026)` | `python3 src/s6_figures.py` |
| `\nNestedRepos` | 64 | results/instruction_coverage.json | `counts.nested` | `python3 src/instruction_census.py --clones /path/to/clones` |
| `\nRuleRepos` | 42 | results/instruction_coverage.json | `counts.rule_files` | `python3 src/instruction_census.py --clones /path/to/clones` |
| `\nImportRepos` | 37 | results/instruction_coverage.json | `counts.import_candidates` | `python3 src/instruction_census.py --clones /path/to/clones` |
| `\nDelegatingRepos` | 125 | results/instruction_coverage.json | `counts.any` | `python3 src/instruction_census.py --clones /path/to/clones` |
| `\nSyncRepoForm` | 0.2 | results/robustness.json | `repository_by_form.insync.est` | `python3 src/s4c_revision.py` |
| `\nSyncRepoFormCI` | -12.7 to 11.7 | results/robustness.json | `repository_by_form.insync.ci` | `python3 src/s4c_revision.py` |
| `\nOpenRepoForm` | 18.7 | results/robustness.json | `repository_by_form.open.est` | `python3 src/s4c_revision.py` |
| `\nOpenRepoFormCI` | 0.4 to 38.9 | results/robustness.json | `repository_by_form.open.ci` | `python3 src/s4c_revision.py` |
| `\nOpenRepoFormRepos` | 24 | results/robustness.json | `repository_by_form.open.matched_repositories` | `python3 src/s4c_revision.py` |
| `\nPrecisionGapBreak` | 25 | results/precision_design.json | `B_breaks.detectable_gap_80pct_two_sided_5pct_conservative` | `python3 src/s4c_revision.py` |
| `\nPrecisionGapSync` | 26 | results/precision_design.json | `S_insync.detectable_gap_80pct_two_sided_5pct_conservative` | `python3 src/s4c_revision.py` |
| `\nAlarmMean` | 0.51 | results/robustness.json | `alarm_burden.mean` | `python3 src/s4c_revision.py` |
| `\nAlarmMedian` | 0 | results/robustness.json | `alarm_burden.median` | `python3 src/s4c_revision.py` |
| `\nAlarmMax` | 30 | results/robustness.json | `alarm_burden.max` | `python3 src/s4c_revision.py` |
| `\nMedOpenExact` | 98.6 | results/summary.json | `repair.context.median_days_open_so_far` | `python3 src/s4_analyze.py` |
| `\nOpenIQR` | 56 to 169 | results/summary.json | `repair.context.iqr_days_open_so_far` | `python3 src/s4_analyze.py` |
| `\nTypeBreakAgents` | 4.7 | results/robustness.json | `dynamics_by_file_type[AGENTS.md].break_rate` | `python3 src/s4c_revision.py` |
| `\nTypeInvAgents` | 13.8 | results/robustness.json | `dynamics_by_file_type[AGENTS.md].invalidation_rate` | `python3 src/s4c_revision.py` |
| `\nTypeBreakClaude` | 10.8 | results/robustness.json | `dynamics_by_file_type[CLAUDE.md].break_rate` | `python3 src/s4c_revision.py` |
| `\nTypeInvClaude` | 21.4 | results/robustness.json | `dynamics_by_file_type[CLAUDE.md].invalidation_rate` | `python3 src/s4c_revision.py` |
| `\nSpellBreakCtx` | 7.0 | results/robustness.json | `presence_spells.context.break_rate_per_100_years` | `python3 src/s4c_revision.py` |
| `\nSpellInvCtx` | 15.8 | results/robustness.json | `presence_spells.context.invalidation_rate_per_100_years` | `python3 src/s4c_revision.py` |
| `\nSpellBreakRd` | 8.5 | results/robustness.json | `presence_spells.readme.break_rate_per_100_years` | `python3 src/s4c_revision.py` |
| `\nSpellInvRd` | 31.4 | results/robustness.json | `presence_spells.readme.invalidation_rate_per_100_years` | `python3 src/s4c_revision.py` |

## Numbers typed by hand in the text

| Claim | Source |
|---|---|
| Inclusion filter: at least 50 stars, at most 150 MB, four file names, six size bands from 500 to 60,000 bytes, first two ranked pages of 100 per query (API cap 1,000), 4,800 of 1,834,808 reported hits | constants in `src/s1_search.py` and `src/s2_select.py`; `results/summary.json` key `funnel` |
| Up to 150 evenly spaced snapshots, bootstrap resamples (2,000, 1,000 and 500, see `results/robustness.json` key `bootstrap_resamples`), ten or more references for a bulk rewrite, breaks older than 30 days, repair within one day or three commits, top two and top five repositories | constants in `src/s3_mine.py`, `src/s4_analyze.py`, `src/s4b_robustness.py` |
| "about twice as often", "about half as often", "one reference in a hundred", "half as much again" | rounded restatements of `nInvRatio`, `nDriftCtx`, `nUpperDriftCtx` over `nLenientDriftCtx` |
| "March 2026", "April 2026" in the worked example | `results/overview_example.json` key `breaks_by_day` |
| Human-derived numbers (macros starting with `h`) | `../manuscript/human_numbers.tex`, written by `src/s11_labelling_agreement.py` from the rater sheets. All render as [PENDING] until the sheets are filled and adjudicated |
| Numbers attributed to other papers (1.27%, 18,048, 230, 612, 356, 23.0%, 32 of 50, 28.9%, 82.3%, over 20%, 124 and 10, 16 of 28, corpus sizes) | the cited papers; those of Treude and Baltes, Tan et al., Gloaguen et al. and dos Santos et al. were read from the PDFs on 4 Oct 2026, see `citation_audit.md` |

# Replication package: reference drift and repair in young agent context files

Everything the paper reports is produced by the code in `src/` and stored in `results/`.

## Reproduce

```
bash run.sh                  # stages 4 to 11 from the mined timelines, about twenty minutes
bash run.sh --from-scratch   # also search, select, clone and mine: about one hour, 0.6 GB in ~/.cache/context-rot-study/S03
```

The mined timelines (19 MB) are shipped in `data/mined/`, with the search hits and the sampled repository list in `data/search/`, so the default path needs nothing outside this folder. If `~/.cache/context-rot-study/S03/mined` exists it is used instead. The clones are not shipped. Without them stage 5 leaves the evidence column of the development sample empty. Stage 10 is not run by default and refuses to run without the clones.

Requirements: Python 3.11+ with pinned dependencies installed via `python3 -m pip install -r requirements.txt`, git 2.40+, and for `--from-scratch` an authenticated `gh` CLI.
A from-scratch run on a later date returns a different sample, because GitHub code search results change.

## Stages

| Stage | Script | Output |
|---|---|---|
| 1 | `src/s1_search.py` | cache `search/hits.jsonl` (4 file names x 6 size bands x 2 pages) |
| 2 | `src/s2_select.py` | cache `search/sample.json` (not fork, not archived, at least 50 stars, at most 150 MB) |
| 3 | `src/s3_mine.py` | cache `mined/<repo>.json.gz` (constraint timelines, break events, file versions, commit log) |
| 4 | `src/s4_analyze.py` | `results/summary.json` and the per-file, per-constraint, per-break, per-removal CSV files |
| 4b | `src/s4b_robustness.py` | `results/robustness.json`: invalidation rates, competing-risk incidence, robustness of the README contrasts, drift sensitivity, mechanical estimate of drift hidden by lenient matching, fully enumerated subset, denominators, stratification by reference form, internal AI spot check |
| 5 | `src/s5_validation_sample.py` | `results/validation_sample.csv` (seed 20261003), the sample behind the provisional AI labels |
| 6 | `src/s6_figures.py` | `../manuscript/figures/*.pdf`, `results/drift_by_age_summary.csv`, `results/overview_example.json` |
| 7 | `src/s7_validation_summary.py` | `results/validation_summary.json` (provisional, AI-assigned labels) |
| 8 | `src/s8_llm_second_rater.py` | `results/llm_second_rater.jsonl` (cache), `results/llm_second_rater_summary.json` |
| 9 | `src/s9_texnumbers.py` | `../manuscript/numbers.tex`, `claims.md` (only macros used in the manuscript) |
| 10 | `src/s10_labelling_kit.py` | `labelling/`: blinded sheets for two raters, key, calibration items. Not part of the default run |
| 11 | `src/s11_labelling_agreement.py` | `results/human_validation.json` and `../manuscript/human_numbers.tex`: kappa, precision per artefact, recall, with intervals. Prints [PENDING] macros while sheets are empty |

`src/compiler.py` is the constraint compiler and checker. `src/rules.py` holds the rule extractor and the solvers.
`results/commit_convention.csv` and the `compliance` block of `results/summary.json` are an exploratory analysis that is not reported in the paper.

## HUMAN LABELLING IS PENDING (action needed from the authors)

No human has labelled anything. The draft explicitly states that labelling is incomplete: every human-derived number is a macro in `../manuscript/human_numbers.tex`, written by stage 11 from the rater sheets. Until all required sheets are filled and adjudicated and `labelling/author_verification.txt` exists, every such macro prints a red [PENDING] and the first page carries a red "DRAFT, NOT FOR SUBMISSION" banner.

Steps for the authors:
1. Two human raters, at least one of whom did not build the pipeline, read `labelling/GUIDELINES.md` and do the calibration round (`labelling/calibration/`).
2. Each fills the five sheets in their folder (about 1,260 judgements each, estimated 12 to 16 hours).
3. `python3 src/s11_labelling_agreement.py` reports kappa and the items to adjudicate. Record adjudications in `labelling/adjudicated.csv` and rerun.
4. Write one or two sentences into `labelling/author_verification.txt` stating what the authors verified (labels, numbers quoted from prior work, claims). This text is printed in the Acknowledgment.
5. Rerun stage 11 and recompile. If precision differs materially between the two artefacts, the RQ2 and RQ3 contrasts must be revisited.

The kit was built once with stage 10 (seed 20261005) and is not rebuilt by `run.sh`. Stage 10 refuses to run without the clones and refuses to overwrite a kit that contains labels. The agreement script was tested end to end on dummy filled sheets in a scratch directory, which was then deleted.

## Development labels and the internal spot check (not evidence)

`results/validation_labels.csv` and `results/conflict_labels.csv` were written by the AI assistant that built this package while developing the compiler. They are reported in the paper only as development labels. The second rater in stage 8 is a local model (qwen2.5:14b, 160 calls) whose kappa with those labels is 0.14.

`results/robustness.json` key `internal_ai_spot_check` records counts (36 of 40 constraints, 28 of 36 breaks) from the project's internal AI-assisted review loop. The reviewers in that loop were AI, not human, item-level labels are not available, and the counts are not used in the paper.

`results/rules.csv`, `results/inconsistency_cores.csv` (a propositional consistency check of command mentions) and `results/commit_convention.csv` are exploratory analyses that are not reported in the paper.

## Not done

No pull request outcome data was collected, so the package contains no causal analysis.

## Additional revision analyses

Stage 4c (`src/s4c_revision.py`) adds presence-spell rates, repository-by-form contrasts, file-type dynamics and alert burden to `results/robustness.json`. Earlier results keys remain unchanged, except the removal of a private review pointer. `caffeinate` and `timeout` are used only when installed. The default run uses shipped mined data when the selected cache has no `mined/` directory.

## Revision checks and incomplete evidence

`python3 src/s12_precision_sensitivity.py` reads the human precision estimates and writes `results/precision_sensitivity.json`, including the D3 gate and an 81-scenario rectangular sensitivity grid (per-artefact estimates and interval endpoints for breaks and in-sync events). It currently reports `pending` and `unevaluated`, because the rater sheets are unfilled. No human precision, corrected contrast or author verification has been inferred.

The independent-item planning approximation in `results/precision_design.json` gives detectable precision gaps of about 25 points for breaks and 26 points for in-sync events at 80% power and a two-sided 5% level. It is not an equivalence analysis. The human precision intervals should not be interpreted as certifying equal precision.

`results/instruction_coverage.json` records a census of the pinned repository heads. To repeat it using local clones, run `python3 src/instruction_census.py --clones /path/to/clones`. It does not fetch missing objects. The normal reproduction path uses the shipped census, since complete trees are not included in the mined timelines.

For rater distribution, send only `GUIDELINES.md`, `calibration/` and that rater's folder. Do not send the entire organiser kit: `key/` and the other rater's files must remain hidden.

The tested Linux path uses the glibc-based `python:3.11-slim` container and the pinned requirements. Alpine requires extra build dependencies for Matplotlib and is not the documented portable path.

The 11 October clean Linux run completed using `python@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce` and `requirements-linux-lock.txt`. Both number files and the claims map were byte-identical to the local build. JSON numerical results differed only by floating-point roundoff (maximum absolute difference 5.51e-11); the development sample evidence column was empty without clones, as documented above.

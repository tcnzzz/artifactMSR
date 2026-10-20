# Labelling guidelines (two human raters, independent and blind)

Status on 4 Oct 2026: **no human has labelled anything.** The sheets in `rater1/` and `rater2/` are empty and the paper prints [PENDING] for every number that depends on them.

## Who

Two human raters. At least one must not have taken part in building the pipeline. Both should be able to read a commit diff. Do not use a language model to produce labels. Do not open `key/`, `results/validation_labels.csv` or the analysis results before you finish.

Expected effort: about 1,260 judgements per rater. Sheets A and L take under a minute per item, R a few seconds per line, B and S two to five minutes per item because the commit must be opened. Plan 12 to 16 hours per rater.

## Procedure

1. **Calibration.** Label the 20 items in `calibration/calibration_items.csv` together, discuss, and write the agreed label in `label_agreed`. These items are outside the samples. If the guidelines turn out to be ambiguous, amend this file before starting and note the change at the bottom.
2. **Independent labelling.** Each rater fills only the sheets in their own folder. The two folders hold the same items in different random orders. Item identifiers are random and carry no information. Do not discuss items until both are done.
3. **Agreement.** Run `python3 src/s11_labelling_agreement.py`. It reports Cohen's kappa per sheet on the labels as given (yes, no, unsure) and lists the items to adjudicate: every disagreement and every item that either rater marked unsure.
4. **Adjudication.** Resolve those items together and record them in `labelling/adjudicated.csv` with the header `id,column,label`. The column name is `is_repo_reference` (A), `true_staleness` (B), `in_sync` (S) or `matched_is_intended` (L). The label may stay `unsure`, in which case the item is excluded from the estimate and counted. Recall (sheet R) is not adjudicated: the script reports each rater's estimate and their mean.
5. **Author statement.** Write `labelling/author_verification.txt` (one or two sentences on what the authors verified). Rerun the script and recompile the paper.

Every item has a link to the file or commit on GitHub at the exact commit that was analysed. Open it whenever the excerpt is not enough.

## Sheet A, extraction (`is_repo_reference`: yes / no / unsure)

Question: in this line, does the extracted text denote a file, directory, package script, build target or build tool manifest that the author expects to be **tracked in this repository**?

- yes: a source file, a directory of the project, a script defined in a package manifest, a make target, a tool the project declares.
- no: a URL, a container image, an import path of a dependency, a branch prefix, a placeholder or example name, a file the agent is asked to create, a build output or cache that is not tracked, a path in another repository, a value that only looks like a path.
- unsure: you cannot tell from the file and the link.

Judge the reference, not whether it currently resolves. The sheet hides the checker's verdict.

## Sheet B, breaks (`true_staleness`: yes / no / unsure, and `reason`)

The sheet mixes context files and README files. Question: did the commit really remove, move or rename a **tracked artefact that the instruction refers to**, while the instruction stayed in the file, so that the line became out of date?

- Open the `commit` link and read the diff. The `commit_record` column is only a hint. For README items the `instruction_context` is the single line that held the reference.
- For `script`, `target`, `manifest` and `dep` items, confirm in the diff of the manifest or makefile that the script, target or declaration was removed or renamed. Plausibility is not enough.
- no, with a reason, when: the artefact is runtime, session or generated state that was merely untracked; the instruction matched an unrelated file that shares a base name or suffix; the instruction asks the agent to create or fill the path; the path is a user configuration file or an example; the commit does not show the removal; the same commit also corrected the instruction.
- unsure when the diff is too large to load or the reference is ambiguous.

## Sheet S, in-sync updates (`target_invalidated`, `reference_updated`: yes / no / unsure)

The checker claims that this one commit both made the referenced artefact disappear and removed or rewrote the reference in the file. Open the commit.

- `target_invalidated`: yes if the diff removes, moves or renames the tracked artefact the reference denotes (same rules as sheet B).
- `reference_updated`: yes if the same commit deletes the reference from the file or rewrites it (for example to the new path). no if the file is only reformatted and the reference is still there, or the whole file was deleted or replaced for unrelated reasons such as a file rename.

The event counts as confirmed only if both are yes.

## Sheet L, lenient matches (`matched_is_intended`: yes / no / unsure)

These references resolve at the head only because some file or directory has the same base name or path suffix. `matched_examples` shows up to five matched locations and `matched_locations` their number. Question: is one of the matched locations the artefact the instruction means? Answer no when the instruction clearly points at a different location or at something that no longer exists.

## Sheet R, recall

The sheet is a uniform random sample of all non-blank lines of 30 context files, whether or not the tool extracted anything from them. `tool_extracted` shows what the tool took from the line.

For each line enter **how many** references to tracked artefacts of this repository the line contains, by kind: `true_path`, `true_script`, `true_target`, `true_manifest`, `true_dep`. Enter 0 where there is none. Use the definition of sheet A. Count a path once per line. A command such as a package-manager call of a named script counts as one `script`. A call of an ecosystem tool counts as one `manifest`. A call of a linter, formatter, type checker or test runner counts as one `dep`.
In `tool_wrong` enter how many of the listed extractions are not genuine references (0 if none).

Most lines contain no reference. The estimate weights each line by the number of lines in its file over the number sampled.

## What the script reports

Kappa before adjudication for A, B, S, L and for "line contains a reference" in R. Precision for A overall and for anchored violations, weighted by stratum size. Precision for B and S separately for context files and README, with the difference. The share of intended matches for L. Recall overall and per kind. Intervals are 95% percentile intervals from a bootstrap within strata (A, B, S), over files (R), or Wilson (L).

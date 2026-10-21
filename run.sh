#!/usr/bin/env bash
# Single entry point. Default: rebuild every result, figure and number from the mined timelines.
#   bash run.sh                 stages 4 to 12 except 10. The labelling kit is NOT rebuilt (python3 src/s10_labelling_kit.py does that, once, with clones). Reads ~/.cache/context-rot-study/S03/mined if present, otherwise data/mined shipped here.
#   bash run.sh --from-scratch  stages 1 to 12 (GitHub search, metadata, partial clones, mining; about one hour, 0.6 GB in the cache)
# The cache location can be changed with S03_CACHE.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
run_bounded() {
  local limit="$1"
  shift
  local prefix=()
  if command -v caffeinate >/dev/null 2>&1; then prefix+=(caffeinate -i); fi
  if command -v timeout >/dev/null 2>&1; then prefix+=(timeout "$limit"); fi
  "${prefix[@]}" "$@"
}
cd "$(dirname "$0")"
if [[ "${1:-}" == "--from-scratch" ]]; then
  run_bounded 1800 python3 src/s1_search.py      # code search, 24 queries / 48 pages, rate limited
  python3 src/s2_select.py                                  # repository metadata and inclusion filter
  run_bounded 7200 python3 src/s3_mine.py --workers 6   # partial clones and constraint timelines
fi
python3 src/rules.py                    # solver self test against brute force
python3 src/s4_analyze.py > results/analyze.log
python3 src/s5_validation_sample.py     # seeded samples behind the provisional AI-assigned labels
python3 src/s7_validation_summary.py > /dev/null
python3 src/s8_llm_second_rater.py > /dev/null   # cached responses; calls local Ollama only for uncached rows
python3 src/s4b_robustness.py > /dev/null        # invalidation rates, competing risks, robustness (four to twelve minutes)
python3 src/s4c_revision.py > /dev/null
python3 src/s6_figures.py
python3 src/s11_labelling_agreement.py > /dev/null   # writes results/human_validation.json and ../manuscript/human_numbers.tex; a macro prints [PENDING] only if its sheet is empty
python3 src/s12_precision_sensitivity.py             # reads results/human_validation.json; writes ../manuscript/sensitivity_numbers.tex
python3 src/s9_texnumbers.py
echo "done: results/ refreshed, figures and numbers.tex written to ../manuscript"

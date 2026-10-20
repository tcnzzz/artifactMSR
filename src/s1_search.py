#!/usr/bin/env python3
"""Stage 1: build the sampling frame of repositories that contain agent context files.

Uses the GitHub REST code search API through the authenticated `gh` CLI.
The API returns at most 1000 hits per query, so we slice each file name by
file-size bands to widen coverage. Output: search/hits.jsonl in the cache.
"""
import json, subprocess, sys, time, os

CACHE = os.path.expanduser(os.environ.get("S03_CACHE", "~/.cache/context-rot-study/S03"))
OUT = os.path.join(CACHE, "search", "hits.jsonl")
FILENAMES = ["AGENTS.md", "CLAUDE.md", ".cursorrules", "copilot-instructions.md"]
SIZE_BANDS = ["500..1500", "1501..3000", "3001..5000", "5001..8000", "8001..15000", "15001..60000"]
PAGES = 2  # 100 hits per page


def gh_search(q, page):
    for attempt in range(6):
        p = subprocess.run(
            ["gh", "api", "-X", "GET", "search/code", "-f", f"q={q}", "-f", "per_page=100",
             "-f", f"page={page}"], capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            return json.loads(p.stdout)
        sys.stderr.write(f"retry {attempt} {q} p{page}: {p.stderr[:200]}\n")
        time.sleep(30)
    return {"items": []}


def main():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            d = json.loads(line)
            done.add((d["query"], d["page"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as f:
        for fn in FILENAMES:
            for band in SIZE_BANDS:
                q = f"filename:{fn} size:{band}"
                for page in range(1, PAGES + 1):
                    if (q, page) in done:
                        continue
                    r = gh_search(q, page)
                    items = [{"repo": it["repository"]["full_name"], "path": it["path"],
                              "fork": it["repository"].get("fork")} for it in r.get("items", [])]
                    f.write(json.dumps({"query": q, "page": page, "filename": fn,
                                        "total_count": r.get("total_count"), "items": items}) + "\n")
                    f.flush()
                    print(q, page, len(items), r.get("total_count"), flush=True)
                    time.sleep(7)  # code search allows 10 requests per minute


if __name__ == "__main__":
    main()

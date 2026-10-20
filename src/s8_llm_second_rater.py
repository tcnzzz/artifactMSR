#!/usr/bin/env python3
"""Stage 8 (optional): a local language model as an independent second rater for validation sets A and B.

Uses the local Ollama server only. Every response is cached in results/llm_second_rater.jsonl, so reruns make no calls.
"""
import csv, json, os, sys, urllib.request, collections

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
MODEL = "qwen2.5:14b"
CACHE = os.path.join(RES, "llm_second_rater.jsonl")
PROMPT_A = """You audit a tool that extracts references to repository files, directories, scripts and build tools from an instruction file for coding agents.
Instruction line: {raw}
Extracted reference ({kind}): {target}
Question: in this line, does the extracted text refer to a file, directory, script, build target or build tool that is expected to be tracked inside this same repository? Answer NO if it is a URL, a container image, a package import, a branch name, an example or placeholder name, a file the agent is asked to create, a build output, or not a path at all.
Answer with exactly one word: YES or NO."""
PROMPT_B = """You audit a detector of stale references in an instruction file for coding agents.
The instruction file still contains this line: {raw}
It refers to ({kind}): {target}
The detector says this reference became invalid in a commit. Commit subject and the changed files that match the reference (A added, D deleted, M modified): {evidence}
Question: was a tracked repository file, directory or script that the instruction refers to really removed, moved or renamed by this commit, so that the instruction line is now out of date? Answer NO if the reference is a runtime or generated file, a user configuration file, an example, or if the evidence does not show the removal.
Answer with exactly one word: YES or NO."""


def ask(prompt):
    req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(
        {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0, "seed": 1, "num_predict": 4}}).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())["response"].strip()


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main():
    cache = {}
    if os.path.exists(CACHE):
        for line in open(CACHE):
            d = json.loads(line)
            cache[d["id"]] = d
    sample = [r for r in csv.DictReader(open(os.path.join(RES, "validation_sample.csv"))) if r["set"] in "AB"]
    labels = {r["id"]: r["label"] for r in csv.DictReader(open(os.path.join(RES, "validation_labels.csv")))}
    calls = 0
    with open(CACHE, "a") as f:
        for r in sample:
            if r["id"] in cache:
                continue
            p = (PROMPT_A if r["set"] == "A" else PROMPT_B).format(**r)
            ans = ask(p)
            calls += 1
            cache[r["id"]] = {"id": r["id"], "model": MODEL, "response": ans}
            f.write(json.dumps(cache[r["id"]]) + "\n")
            f.flush()
    out = {"model": MODEL, "calls_total": len(cache), "calls_this_run": calls}
    for s, pos in (("A", "genuine reference"), ("B", "true staleness")):
        pairs = [(labels[r["id"]] == pos, cache[r["id"]]["response"].upper().startswith("YES")) for r in sample if r["set"] == s]
        po, k = kappa(pairs)
        out[s] = {"n": len(pairs), "ai_label_positive": sum(a for a, _ in pairs), "model_positive": sum(b for _, b in pairs),
                  "raw_agreement": po, "cohen_kappa": k,
                  "unparsed": sum(1 for r in sample if r["set"] == s and not cache[r["id"]]["response"].upper().startswith(("YES", "NO")))}
    json.dump(out, open(os.path.join(RES, "llm_second_rater_summary.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Rule extraction and consistency checking for tool-usage directives in context files.

A context file is mapped to a set of propositional clauses over atoms
  use(T)        the agent uses tool T
  cmd(T S)      the agent runs sub-command S of tool T
  cond(h)       an opaque condition named in an "if/when/after/before" directive
Clause forms produced
  unit+   "use pnpm", or a command line that invokes the tool
  unit-   "never use npm", "do not run `git push --force`"
  horn    "if/when C, run X" (C -> X), "if/when C, never X" (not C or not X)
  choice  "use X or Y", "unless C, do X"  (two positive literals, not Horn)
Background axioms cmd(T S) -> use(T) are Horn and are counted separately.

The solvers: unit propagation (complete for Horn sets) and DPLL (complete in general),
plus deletion-based extraction of a minimal unsatisfiable core.
"""
import re, hashlib, itertools, random

TOOLS = ["npm", "yarn", "pnpm", "bun", "pip", "poetry", "uv", "pipenv", "conda", "jest", "vitest", "mocha", "pytest",
         "unittest", "eslint", "prettier", "biome", "black", "ruff", "flake8", "pylint", "mypy", "pyright", "git",
         "docker", "make", "cargo", "npx", "webpack", "vite", "tsc", "gradle", "maven", "mvn", "bazel", "deno", "node",
         "playwright", "cypress", "isort", "tox", "nox", "just", "turbo", "nx", "lerna", "rebase", "sudo"]
TOOL_RX = "(?:" + "|".join(sorted(map(re.escape, TOOLS), key=len, reverse=True)) + ")"
T = rf"`?(?P<tool>{TOOL_RX})(?P<sub>(?:[ \t]+(?!or\b|and\b|for\b|to\b|as\b|in\b|if\b|when\b|not\b|instead\b|with\b|on\b|is\b|the\b|a\b)[a-z][a-z0-9:\-]+)?)(?P<flag>(?:[ \t]+--?[a-z][a-z\-]+)?)`?(?![A-Za-z0-9_/\-]|\.[A-Za-z0-9])"
NEG_RX = re.compile(r"(?<![a-z])(?:do not|don't|dont|never|avoid|must not|should not|shouldn't|cannot|can't|no longer|not allowed to|forbidden to|refrain from)"
                    r"(?:[ \t]+(?:ever|directly|manually|just|simply|try to|attempt to))?"
                    r"[ \t]+(?:use|run|call|invoke|install with|execute|using|running|calling|rely on|add|introduce|reach for)[ \t]+(?:the[ \t]+)?" + T, re.I)
NEG2_RX = re.compile(r"(?:instead of|rather than|\bnot|\bnever|\bno|\bover|\bavoid|don't use|do not use)[ \t]+(?:using[ \t]+|running[ \t]+)?" + T, re.I)
POS_RX = re.compile(r"(?<![a-z])(?:always use|must use|should use|we use|uses|use|using|run|prefer|managed (?:with|by|via)|powered by|via|with)[ \t]+(?:the[ \t]+)?" + T, re.I)
CHOICE_RX = re.compile(r"(?<![a-z])(?:use|run|using|with|via|either)[ \t]+`?(?P<a>" + TOOL_RX + r")`?[ \t]+or[ \t]+`?(?P<b>" + TOOL_RX + r")`?(?![A-Za-z0-9_/\-]|\.[A-Za-z0-9])", re.I)
NEG_LIST_RX = re.compile(r"`?[ \t]*(?:,|/|or|and|nor|,[ \t]*or)[ \t]*(?:not[ \t]+)?" + T, re.I)
COND_RX = re.compile(r"^\W*(?:\*\*)?(if|when|whenever|after|before|once|unless)\b(?P<cond>[^,:.]{3,80})[,:]", re.I)
CODE_CMD = re.compile(r"`([^`\n]{2,120})`")
FENCE = re.compile(r"^\s*(```+|~~~+)\s*([A-Za-z0-9_+\-]*)")
SUBCMD_TOOLS = {"git", "docker", "npm", "pnpm", "yarn", "bun", "cargo", "pip", "uv", "poetry", "make", "npx"}


AMBIGUOUS = {"just", "make", "node", "black", "nx", "tox", "nox", "sudo", "rebase", "bun", "uv", "vite", "turbo", "deno"}


def ok_prose(m, sent):
    """Tool names that are also English words count in prose only when written as code."""
    t = m.group("tool")
    if t.lower() not in AMBIGUOUS:
        return True
    return m.start("tool") > 0 and sent[m.start("tool") - 1] == "`" and t == t.lower()


def atom_use(t):
    return f"use({t.lower()})"


def atom_cmd(t, s):
    return f"cmd({t.lower()} {s.lower()})"


def cond_atom(text):
    norm = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
    return "cond(" + hashlib.md5(norm.encode()).hexdigest()[:8] + ")"


RUNLIKE = {"run", "run-script", "compose", "workspace", "exec", "stash", "submodule", "remote", "worktree"}


def cmd_atom(tokens, axioms):
    """Most specific atom for a command token list, with Horn axioms linking it to its generalisations."""
    tool = tokens[0].lower()
    rest = [t.lower().strip("`,;:)") if t.strip("`,;:)") in (".", "-A") else t.lower().strip("`.,;:)") for t in tokens[1:]]
    if tool not in SUBCMD_TOOLS or not rest or not re.fullmatch(r"[a-z][a-z0-9:\-]+", rest[0]):
        return atom_use(tool)
    base = f"cmd({tool} {rest[0]})"
    axioms.add((("-", base), ("+", atom_use(tool))))
    if rest[0] in RUNLIKE and len(rest) > 1 and re.fullmatch(r"[a-z0-9][a-z0-9:_.\-]*", rest[1]):
        a = f"cmd({tool} {rest[0]} {rest[1]})"
        axioms.add((("-", a), ("+", base)))
        return a
    flag = next((t for t in rest[1:4] if re.fullmatch(r"--?[a-z][a-z\-]*", t) or t in (".", "-a")), None)
    if flag:
        a = f"cmd({tool} {rest[0]} {flag})"
        axioms.add((("-", a), ("+", base)))
        return a
    return base


def target_atom(m, axioms, sent=""):
    toks = [m.group("tool")]
    if (m.group("sub") or "").strip():
        toks.append(m.group("sub").strip())
        tail = sent[m.end("sub"):m.end("sub") + 40]
        tail = tail.split("`")[0] if "`" in sent[m.start("tool") - 1:m.start("tool")] else (m.group("flag") or "")
        toks += tail.split()[:3]
    return cmd_atom(toks, axioms)


def extract_rules(text):
    """Return (rules, axioms). A rule is dict(clause=tuple of (sign, atom), form, line, text)."""
    rules, axioms = [], set()
    in_fence, lang = False, ""
    for ln, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if m:
            in_fence = not in_fence
            lang = m.group(2).lower()
            continue
        if in_fence:
            s = re.sub(r"^\s*\$\s+", "", line.strip())
            if not s or s.startswith("#"):
                continue
            if lang in ("", "bash", "sh", "shell", "zsh", "console"):
                toks = s.split()
                if toks and toks[0].lower() in TOOLS:
                    add_cmd(toks, ln, line, rules, axioms, None)
            continue
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z`*\-])", line):
            if not sent.strip():
                continue
            cm = COND_RX.match(sent.strip())
            cond = None
            if cm:
                cond = (cm.group(1).lower(), cond_atom(cm.group("cond")))
            negspans, used = [], []
            for m in list(NEG_RX.finditer(sent)) + list(NEG2_RX.finditer(sent)):
                span = m.span("tool")
                if any(span == u for u in used):
                    continue
                used.append(span)
                if not ok_prose(m, sent):
                    continue
                a = target_atom(m, axioms, sent)
                mk_rule(rules, [("-", a)], cond, ln, sent)
                # "never use npm or yarn": the prohibition distributes over the listed tools
                pos = m.end()
                while True:
                    m2 = NEG_LIST_RX.match(sent, pos)
                    if not m2:
                        break
                    used.append(m2.span("tool"))
                    if ok_prose(m2, sent):
                        mk_rule(rules, [("-", target_atom(m2, axioms, sent))], cond, ln, sent)
                    pos = m2.end()
            has_neg = bool(used)
            ch = set()
            for m in CHOICE_RX.finditer(sent):
                if any(m.span("a") == u or m.span("b") == u for u in used):
                    continue
                ch |= {m.span("a"), m.span("b")}
                mk_rule(rules, [("+", atom_use(m.group("a"))), ("+", atom_use(m.group("b")))], cond, ln, sent)
            for m in POS_RX.finditer(sent):
                span = m.span("tool")
                if span in used or span in ch:
                    continue
                used.append(span)
                if ok_prose(m, sent):
                    mk_rule(rules, [("+", target_atom(m, axioms, sent))], cond, ln, sent)
            for m in CODE_CMD.finditer(sent):
                if has_neg:
                    break  # a sentence with a prohibition does not also yield positive command units
                toks = m.group(1).strip().lstrip("$ ").split()
                if len(toks) >= 2 and toks[0].lower() in TOOLS:
                    # skip spans already consumed by a negative or positive pattern
                    st = m.start(1)
                    if any(st <= u[0] <= m.end(1) for u in used):
                        continue
                    add_cmd(toks, ln, sent, rules, axioms, cond)
    # deduplicate identical clauses, keep first occurrence
    seen, out = set(), []
    for r in rules:
        k = tuple(sorted(r["clause"]))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out, sorted(axioms)


def add_cmd(toks, ln, text, rules, axioms, cond):
    mk_rule(rules, [("+", cmd_atom(toks, axioms))], cond, ln, text, form_hint="cmd")


def mk_rule(rules, lits, cond, ln, text, form_hint=""):
    lits = list(lits)
    if cond:
        kw, catom = cond
        lits.append(("+", catom) if kw == "unless" else ("-", catom))
    npos = sum(1 for s, _ in lits if s == "+")
    if npos >= 2:
        form = "choice"
    elif len(lits) == 1:
        form = "unit+" if npos else "unit-"
    else:
        form = "horn-definite" if npos == 1 else "horn-negative"
    rules.append({"clause": tuple(lits), "form": form, "line": ln, "text": text.strip()[:240], "src": form_hint or "prose"})


def is_horn(clause):
    return sum(1 for s, _ in clause if s == "+") <= 1


# ----------------------------------------------------------------------------
# solvers
# ----------------------------------------------------------------------------
def horn_sat(clauses):
    """Unit propagation to the least model. Complete for Horn clause sets. Returns True if satisfiable."""
    true = set()
    changed = True
    while changed:
        changed = False
        for c in clauses:
            neg = [a for s, a in c if s == "-"]
            pos = [a for s, a in c if s == "+"]
            if all(a in true for a in neg):
                if not pos:
                    return False
                if pos[0] not in true:
                    true.add(pos[0])
                    changed = True
    return True


def dpll(clauses, assign=None):
    """Complete satisfiability check for arbitrary clause sets."""
    assign = dict(assign or {})
    while True:
        unit = None
        for c in clauses:
            val, free = False, []
            for s, a in c:
                if a in assign:
                    if assign[a] == (s == "+"):
                        val = True
                        break
                else:
                    free.append((s, a))
            if val:
                continue
            if not free:
                return False
            if len(free) == 1:
                unit = free[0]
                break
        if unit is None:
            break
        assign[unit[1]] = unit[0] == "+"
    atoms = {a for c in clauses for _, a in c} - set(assign)
    if not atoms:
        return True
    a = min(atoms)
    return dpll(clauses, {**assign, a: True}) or dpll(clauses, {**assign, a: False})


def satisfiable(clauses):
    clauses = [tuple(c) for c in clauses]
    if all(is_horn(c) for c in clauses):
        return horn_sat(clauses)
    return dpll(clauses)


def minimal_core(rule_clauses, axioms):
    """Deletion-based minimal unsatisfiable subset of the rule clauses (axioms are always kept)."""
    core = list(rule_clauses)
    i = 0
    while i < len(core):
        trial = core[:i] + core[i + 1:]
        if not satisfiable(trial + list(axioms)):
            core = trial
        else:
            i += 1
    return core


def all_cores(rule_clauses, axioms, limit=20):
    """Enumerate disjoint-ish minimal cores by removing one clause of each found core (the negative unit when present)."""
    rest, cores = list(rule_clauses), []
    while len(cores) < limit and not satisfiable(rest + list(axioms)):
        core = minimal_core(rest, axioms)
        cores.append(core)
        drop = next((c for c in core if all(s == "-" for s, _ in c)), core[0])
        # remove only one clause so that other conflicts with the same prohibition are still found
        other = [c for c in core if c != drop]
        rest.remove(other[0] if other else drop)
    return cores


def self_test(n=3000, seed=1):
    """Compare both solvers against brute force on random clause sets."""
    rng = random.Random(seed)
    for _ in range(n):
        k = rng.randint(1, 5)
        atoms = [f"a{i}" for i in range(k)]
        horn_only = rng.random() < 0.5
        cls = []
        for _ in range(rng.randint(1, 8)):
            w = rng.randint(1, 3)
            c = tuple((rng.choice("+-"), rng.choice(atoms)) for _ in range(w))
            c = tuple(dict.fromkeys(c))
            if horn_only and not is_horn(c):
                continue
            cls.append(c)
        brute = any(all(any((bits[atoms.index(a)] == 1) == (s == "+") for s, a in c) for c in cls)
                    for bits in itertools.product([0, 1], repeat=k))
        assert satisfiable(cls) == brute, cls
        assert dpll(cls) == brute, cls
        if not brute:
            core = minimal_core(cls, [])
            assert not satisfiable(core)
            for i in range(len(core)):
                assert satisfiable(core[:i] + core[i + 1:])
    return n


if __name__ == "__main__":
    import sys
    print("self test ok on", self_test(), "random clause sets")
    if len(sys.argv) > 1:
        rs, ax = extract_rules(open(sys.argv[1]).read())
        for r in rs:
            print(r["line"], r["form"], r["clause"], "|", r["text"][:80])
        cl = [r["clause"] for r in rs]
        print("satisfiable:", satisfiable(cl + ax))

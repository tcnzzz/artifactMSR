#!/usr/bin/env python3
"""Constraint compiler: turns the text of an agent context file into checkable
integrity constraints over a repository snapshot.

Constraint kinds
  path    a file, directory or glob must exist in the tree
  script  a package script (npm, pnpm, yarn, bun) must be defined in a package manifest
  target  a make target, just recipe or task must be defined
  manifest the manifest of an ecosystem tool must exist (cargo needs a cargo manifest, ...)
  dep     a tool invoked in a command must be declared in a dependency manifest or have a config file

A snapshot is described by a RepoState (set of paths plus the text of manifest files).
"""
import re, json, fnmatch, posixpath
from dataclasses import dataclass, field

# ----------------------------------------------------------------------------
# lexical helpers
# ----------------------------------------------------------------------------
FILE_EXT = set("""py js jsx ts tsx mjs cjs json jsonc yml yaml toml md mdx rst txt sh bash zsh ps1 bat cmd go rs java kt kts
swift c h cc cpp hpp cs fs rb php pl lua r jl scala clj ex exs erl hs ml mli dart vue svelte astro html htm css scss sass
less sql graphql gql proto xml gradle cfg ini conf env lock mk cmake tf hcl nix dockerfile ipynb csv tsv png svg jpg gif
snap tmpl tpl j2 hbs ejs prisma sol zig nim v sv tex bib mod sum plist xcodeproj pbxproj sln csproj props targets""".split())
ROOT_FILES = {"Makefile", "Dockerfile", "Justfile", "justfile", "Rakefile", "Gemfile", "Procfile", "LICENSE",
              "README", "CHANGELOG", "CONTRIBUTING", "Taskfile", "Vagrantfile", "Brewfile", "Pipfile", "Jenkinsfile",
              "Caddyfile", "Tiltfile", "BUILD", "WORKSPACE", "CODEOWNERS", "Cargo.toml", "go.mod"}
PATH_CHARS = re.compile(r"^[A-Za-z0-9_@.\-+/\[\]()*~ ]+$")
SYSTEM_PREFIX = ("usr/", "etc/", "tmp/", "var/", "home/", "opt/", "bin/", "dev/", "proc/", "Users/", "root/", "mnt/")


def clean_token(tok):
    t = tok.strip().strip("\"'")
    t = re.sub(r"[.,;:!?)]+$", "", t) if not re.search(r"\.[A-Za-z0-9]+\)?$", t) else t.rstrip(",;:!?")
    t = re.sub(r"(:\d+(-\d+)?|#L\d+(-L?\d+)?)$", "", t)   # line suffixes
    t = t.split("#")[0] if "#" in t and not t.startswith("#") else t
    return t


def path_candidate(tok, from_link=False):
    """Return a normalised path string if tok looks like a repository path, else None."""
    t = clean_token(tok)
    if not t or len(t) > 200 or " " in t:
        return None
    if "://" in t or t.startswith(("http:", "https:", "mailto:", "git@", "www.", "#", "~", "$", "-")):
        return None
    if any(c in t for c in "<>{}$|=`\\\"'%&^,;") or "..." in t or "…" in t:
        return None
    if not PATH_CHARS.match(t) or t.count("(") != t.count(")") or t.count("[") != t.count("]"):
        return None
    if re.search(r"(^|/)\d+(/\d+)+$", t):
        return None  # numeric alternations such as 400/500/600
    if t.startswith("/"):
        return None  # ambiguous with URL routes and absolute system paths
    if t.startswith("@"):
        return None  # scoped package name
    while t.startswith("./"):
        t = t[2:]
    if t.startswith("../") or "/../" in t:
        return None
    isdir = t.endswith("/")
    t = t.rstrip("/")
    if not t or t in (".", ".."):
        return None
    if t.startswith(SYSTEM_PREFIX) or t.startswith(("node_modules", "localhost")):
        return None
    base = t.rsplit("/", 1)[-1]
    ext = base.rsplit(".", 1)[-1].lower() if "." in base[1:] else ""
    has_slash = "/" in t
    if re.fullmatch(r"[\d.]+", t) or re.fullmatch(r"v?\d+(\.\d+)+.*", base) and not has_slash:
        return None  # version numbers
    if has_slash:
        segs = t.split("/")
        if any(s == "" for s in segs):
            return None
        if not isdir and not ext and not from_link and not base.startswith("."):
            # slash token without extension and without trailing slash: "and/or", "owner/repo", "input/output".
            # keep only if it has three or more segments or a segment that looks like a source directory
            if len(segs) < 3 and segs[0] not in COMMON_DIRS and not segs[0].startswith("."):
                return None
        if ext and ext not in FILE_EXT and not from_link and len(segs) < 2:
            return None
        return t + ("/" if isdir else "")
    # bare name
    if isdir:
        return t + "/" if re.fullmatch(r"[A-Za-z0-9_.\-]+", t) else None
    if ext in FILE_EXT and re.fullmatch(r"[A-Za-z0-9_.\-\[\]()*+]+", t) and len(base) > len(ext) + 1:
        if re.fullmatch(r"[A-Z][A-Za-z0-9]*\.[a-z][A-Za-z0-9]*", t) and ext not in FILE_EXT:
            return None
        return t
    if t in ROOT_FILES or (from_link and re.fullmatch(r"[A-Za-z0-9_.\-]+", t)):
        return t
    if t.startswith(".") and re.fullmatch(r"\.[a-z][a-z0-9_.\-]+", t) and t.lstrip(".").split(".")[0] in DOTFILES:
        return t
    return None


COMMON_DIRS = {"src", "lib", "app", "apps", "packages", "pkg", "cmd", "internal", "test", "tests", "docs", "doc",
               "scripts", "tools", "bin", "config", "configs", "examples", "public", "assets", "components", "pages",
               "server", "client", "api", "web", "backend", "frontend", "core", "utils", "crates", "modules",
               "services", "plugins", "e2e", "spec", "specs", "benchmarks", "bench", "include", "source", "sources",
               "resources", "templates", "static", "styles", "hooks", "types", "models", "ui", "cli", "infra",
               "deploy", "ci", "build", "third_party", "vendor", "extensions", "integrations", "libs", "testing"}
DOTFILES = {"github", "gitignore", "env", "eslintrc", "prettierrc", "editorconfig", "dockerignore", "npmrc", "nvmrc",
            "cursor", "claude", "vscode", "husky", "gitattributes", "babelrc", "flake8", "pylintrc", "rubocop",
            "golangci", "pre-commit-config", "cursorrules", "gitmodules", "tool-versions", "python-version",
            "node-version", "changeset", "devcontainer", "circleci", "gitlab-ci", "storybook", "codex", "agents"}

# ----------------------------------------------------------------------------
# command parsing
# ----------------------------------------------------------------------------
PKG_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
PM_BUILTINS = {
    "npm": {"install", "i", "ci", "add", "exec", "init", "publish", "link", "update", "audit", "version", "pack",
            "uninstall", "outdated", "ls", "list", "cache", "config", "login", "rebuild", "prune", "dedupe", "create",
            "view", "info", "pkg", "explain", "why", "help", "root", "prefix", "whoami", "remove", "rm", "up", "x"},
    "pnpm": {"install", "i", "add", "exec", "dlx", "init", "publish", "link", "update", "up", "audit", "remove", "rm",
             "outdated", "ls", "list", "store", "config", "why", "import", "rebuild", "prune", "dedupe", "create",
             "env", "patch", "pack", "setup", "fetch", "deploy", "approve-builds", "self-update", "licenses", "root",
             "bin", "help", "unlink", "recursive", "changeset", "tsc", "vitest", "eslint", "prettier", "tsx", "turbo",
             "nx", "jest", "playwright", "biome", "prisma", "drizzle-kit", "wrangler", "vite", "next", "tsup", "oxlint",
             "knip", "astro", "expo", "cap", "tauri", "electron", "supabase", "node", "ts-node", "vue-tsc", "svelte-check"},
    "yarn": {"install", "add", "exec", "dlx", "init", "publish", "link", "up", "upgrade", "audit", "remove", "why",
             "set", "config", "cache", "workspaces", "plugin", "npm", "info", "list", "pack", "rebuild", "dedupe",
             "create", "global", "import", "node", "version", "constraints", "patch", "unlink", "help", "outdated",
             "tsc", "jest", "eslint", "prettier", "vitest", "upgrade-interactive", "bin", "generate-lock-entry"},
    "bun": {"install", "i", "add", "x", "init", "publish", "link", "update", "remove", "rm", "pm", "create", "upgrade",
            "build", "test", "outdated", "patch", "unlink", "repl", "exec", "why", "audit", "info"},
}
IMPLICIT_SCRIPTS = {"npm": {"test", "start", "stop", "restart", "t"}}
VALUE_FLAGS = {"--filter", "-F", "--prefix", "-C", "--cwd", "-w", "--workspace", "--dir", "--scope", "--stream-prefix",
               "-f", "--file", "--config", "-c", "-j", "--jobs"}

MANIFEST_NEEDS = {  # command head -> list of alternative manifest path patterns (basename match anywhere)
    "cargo": ["Cargo.toml"], "go": ["go.mod", "go.work"], "npm": ["package.json"], "pnpm": ["package.json"],
    "yarn": ["package.json"], "bun": ["package.json"], "npx": ["package.json"], "bunx": ["package.json"],
    "mvn": ["pom.xml"], "./mvnw": ["mvnw"], "gradle": ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"],
    "./gradlew": ["gradlew"], "bundle": ["Gemfile"], "rake": ["Rakefile"], "composer": ["composer.json"],
    "poetry": ["pyproject.toml"], "uv": ["pyproject.toml", "uv.lock", "requirements.txt"], "pipenv": ["Pipfile"],
    "tox": ["tox.ini", "pyproject.toml", "setup.cfg"], "nox": ["noxfile.py"], "make": ["Makefile", "makefile", "GNUmakefile"],
    "just": ["justfile", "Justfile", ".justfile"], "task": ["Taskfile.yml", "Taskfile.yaml", "taskfile.yml", "taskfile.yaml"],
    "mix": ["mix.exs"], "dotnet": ["*.sln", "*.csproj", "*.fsproj", "*.slnx"], "swift": ["Package.swift"],
    "flutter": ["pubspec.yaml"], "dart": ["pubspec.yaml"], "deno": ["deno.json", "deno.jsonc", "package.json"],
    "bazel": ["WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel"], "cmake": ["CMakeLists.txt"], "tsc": ["tsconfig.json", "tsconfig*.json"],
    "pre-commit": [".pre-commit-config.yaml"], "turbo": ["turbo.json", "turbo.jsonc"], "nx": ["nx.json"],
    "docker-compose": ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml", "docker-compose*.yml", "compose*.yaml"],
    "zig": ["build.zig"], "stack": ["stack.yaml"], "cabal": ["*.cabal"], "sbt": ["build.sbt"], "lerna": ["lerna.json"],
    "wrangler": ["wrangler.toml", "wrangler.json", "wrangler.jsonc"], "terraform": ["*.tf"], "alembic": ["alembic.ini"],
}
PY_TOOLS = {"pytest", "ruff", "mypy", "black", "flake8", "isort", "pylint", "pyright", "bandit", "coverage", "sphinx-build",
            "mkdocs", "tox", "nox", "pre-commit", "maturin", "hatch", "pdm", "ty", "basedpyright", "pyupgrade", "codespell"}
PY_CONFIG = {"pytest": ["pytest.ini", "conftest.py"], "ruff": ["ruff.toml", ".ruff.toml"], "mypy": ["mypy.ini", ".mypy.ini"],
             "flake8": [".flake8"], "pylint": [".pylintrc", "pylintrc"], "pyright": ["pyrightconfig.json"],
             "mkdocs": ["mkdocs.yml"], "tox": ["tox.ini"], "nox": ["noxfile.py"], "pre-commit": [".pre-commit-config.yaml"],
             "coverage": [".coveragerc"], "sphinx-build": ["conf.py"], "isort": [".isort.cfg"], "codespell": [".codespellrc"]}
JS_TOOLS = {"eslint", "prettier", "jest", "vitest", "tsc", "playwright", "biome", "turbo", "nx", "webpack", "vite", "mocha",
            "cypress", "tsx", "ts-node", "rollup", "esbuild", "tsup", "oxlint", "knip", "changeset", "lerna", "husky",
            "lint-staged", "prisma", "drizzle-kit", "next", "astro", "svelte-check", "vue-tsc", "stylelint", "storybook",
            "wrangler", "nodemon", "ava", "c8", "nyc", "typedoc", "lefthook", "commitlint", "syncpack", "publint"}
JS_PKG = {"tsc": ["typescript"], "playwright": ["@playwright/test", "playwright"], "biome": ["@biomejs/biome"],
          "changeset": ["@changesets/cli"], "commitlint": ["@commitlint/cli"], "next": ["next"]}
SCRIPT_RUNNERS = {"bash", "sh", "zsh", "python", "python3", "node", "tsx", "ts-node", "deno", "ruby", "php", "source", ".",
                  "pwsh", "powershell", "Rscript", "perl", "lua"}
COMMAND_HEADS = (set(MANIFEST_NEEDS) | PY_TOOLS | JS_TOOLS | SCRIPT_RUNNERS | PKG_MANAGERS |
                 {"git", "docker", "cd", "pip", "pip3", "npx", "bunx", "uvx", "pipx", "gh", "curl", "cat", "ls", "rm", "cp",
                  "mv", "mkdir", "echo", "export", "grep", "rg", "find", "sed", "open", "brew", "apt", "apt-get", "sudo"})


@dataclass
class Constraint:
    kind: str      # path | script | target | manifest | dep
    target: str
    line: int
    raw: str
    sub: str = ""  # sub kind: link, code, cmd-arg, glob, npm, make, just, task ...

    @property
    def key(self):
        return f"{self.kind}:{self.sub if self.kind in ('script', 'target') else ''}:{self.target}"


def split_commands(line):
    line = re.sub(r"^\s*(\$|>|%|#\s*\$)\s+", "", line)
    line = re.sub(r"\s+#\s.*$", "", line)
    parts = re.split(r"\s*(?:&&|\|\||;|\|)\s*", line)
    return [p.strip() for p in parts if p.strip()]


def strip_prefix(tokens):
    while tokens and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]) or tokens[0] in ("sudo", "time", "env", "exec", "command")):
        tokens = tokens[1:]
    return tokens


def positional(tokens):
    out, skip = [], False
    for t in tokens:
        if skip:
            skip = False
            continue
        if t in VALUE_FLAGS:
            skip = True
            continue
        if t == "--":
            continue
        if t.startswith("-"):
            continue
        out.append(t)
    return out


def parse_command(cmd, line_no, raw, out):
    try:
        tokens = cmd.split()
    except Exception:
        return
    tokens = strip_prefix(tokens)
    if not tokens:
        return
    head = tokens[0]
    args = tokens[1:]
    C = lambda kind, target, sub="": out.append(Constraint(kind, target, line_no, raw.strip()[:200], sub))
    if any(ch in cmd for ch in "<>{}") or "..." in cmd or "$(" in cmd or "`" in cmd:
        placeholder = True
    else:
        placeholder = False
    # wrappers
    if head in ("uv", "poetry", "pipenv", "pdm", "hatch", "rye") and len(args) >= 2 and args[0] == "run":
        C("manifest", head, "tool") if head in MANIFEST_NEEDS else None
        rest = positional(args[1:]) if head != "uv" else [a for a in args[1:] if not a.startswith("-")]
        if rest:
            parse_command(" ".join(args[args.index(rest[0]):]), line_no, raw, out)
        return
    if head in ("npx", "bunx", "pnpx") or (head in ("pnpm", "yarn", "bun") and args[:1] in (["exec"], ["dlx"], ["x"])):
        rest = args if head in ("npx", "bunx", "pnpx") else args[1:]
        rest = [a for a in rest if not a.startswith("-")]
        if head in ("pnpm", "yarn", "bun"):
            C("manifest", head, "tool")
        if rest and not placeholder:
            tool = rest[0].split("@")[0] if not rest[0].startswith("@") else rest[0]
            if tool in JS_TOOLS and not (head in ("pnpm", "yarn") and args[:1] == ["dlx"]):
                C("dep", tool, "js")
        return
    if head == "docker" and args[:1] == ["compose"]:
        C("manifest", "docker-compose", "tool")
        return
    if head in PKG_MANAGERS:
        C("manifest", head, "tool")
        pos = positional(args)
        if not pos or placeholder:
            return
        script = None
        if pos[0] in ("run", "run-script") and len(pos) > 1:
            script = pos[1]
        elif head == "yarn" and pos[0] == "workspace" and len(pos) > 2:
            script = pos[2] if pos[2] != "run" else (pos[3] if len(pos) > 3 else None)
            if script in PM_BUILTINS["yarn"]:
                script = None
        elif head == "npm" and pos[0] in IMPLICIT_SCRIPTS["npm"]:
            script = "test" if pos[0] in ("t", "test") else None
        elif head in ("pnpm", "yarn", "bun") and pos[0] not in PM_BUILTINS[head] and pos[0] not in ("run",):
            script = pos[0]
        if script and re.fullmatch(r"[A-Za-z0-9_:.\-/]+", script):
            C("script", script, "pkg")
        return
    if head == "make":
        C("manifest", "make", "tool")
        if placeholder:
            return
        for a in positional(args):
            if "=" in a:
                continue
            if re.fullmatch(r"[A-Za-z0-9_.\-/]+", a):
                C("target", a, "make")
        return
    if head in ("just", "task"):
        C("manifest", head, "tool")
        pos = positional(args)
        if pos and not placeholder and re.fullmatch(r"[A-Za-z0-9_:.\-]+", pos[0]):
            C("target", pos[0], head)
        return
    if head in SCRIPT_RUNNERS:
        pos = [a for a in args if not a.startswith("-")]
        if head in ("python", "python3") and "-m" in args:
            i = args.index("-m")
            if i + 1 < len(args) and args[i + 1].replace("_", "-") in PY_TOOLS:
                C("dep", args[i + 1].replace("_", "-"), "py")
            return
        if head == "deno":
            C("manifest", "deno", "tool")
            return
        if "-c" in args or "-e" in args:
            return
        if pos and not placeholder:
            p = path_candidate(pos[0])
            if p and ("/" in p or "." in p):
                C("path", p, "script-file")
        return
    if head.startswith("./") and not placeholder:
        if head in MANIFEST_NEEDS:
            C("manifest", head, "tool")
        else:
            p = path_candidate(head)
            if p:
                C("path", p, "script-file")
        return
    if head in PY_TOOLS:
        C("dep", head, "py")
        return
    if head in JS_TOOLS:
        C("dep", head, "js")
        return
    if head in MANIFEST_NEEDS:
        C("manifest", head, "tool")
        return


FENCE = re.compile(r"^\s*(```+|~~~+)\s*([A-Za-z0-9_+\-]*)")
SHELL_LANGS = {"bash", "sh", "shell", "zsh", "console", "terminal", "shellscript", "fish", "powershell", "bat", "cmd", "ps1"}
INLINE = re.compile(r"(?<!`)`([^`\n]{1,200})`(?!`)")
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def compile_text(text):
    """Return the list of constraints compiled from a context file's text (deduplicated by key)."""
    out = []
    in_fence, fence_lang, fence_mark = False, "", ""
    for i, line in enumerate(text.splitlines(), 1):
        m = FENCE.match(line)
        if m:
            if not in_fence:
                in_fence, fence_lang, fence_mark = True, m.group(2).lower(), m.group(1)[:3]
            elif line.strip().startswith(fence_mark):
                in_fence = False
            continue
        if in_fence:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("//"):
                continue
            if fence_lang in SHELL_LANGS or fence_lang == "":
                for cmd in split_commands(s):
                    toks = strip_prefix(cmd.split())
                    if not toks:
                        continue
                    if fence_lang == "" and not (toks[0] in COMMAND_HEADS or toks[0].startswith("./")):
                        continue
                    parse_command(cmd, i, line, out)
            continue
        for m in LINK.finditer(line):
            p = path_candidate(m.group(1), from_link=True)
            if p:
                out.append(Constraint("path", p, i, line.strip()[:200], "link"))
        for m in INLINE.finditer(line):
            span = m.group(1).strip()
            toks = span.split()
            if not toks:
                continue
            first = strip_prefix(re.sub(r"^\$\s+", "", span).split())
            if first and (first[0] in COMMAND_HEADS and len(first) >= 2 or first[0].startswith("./") and len(first) >= 1 and "/" in first[0][2:] + "/"):
                for cmd in split_commands(span):
                    parse_command(cmd, i, line, out)
                if first[0].startswith("./") and len(first) == 1:
                    pass
                continue
            if len(toks) == 1:
                p = path_candidate(span)
                if p:
                    out.append(Constraint("path", p, i, line.strip()[:200], "glob" if "*" in p else "code"))
    seen, uniq = set(), []
    for c in out:
        if c.kind == "path" and "*" in c.target:
            c.sub = "glob"
        if c.key not in seen:
            seen.add(c.key)
            uniq.append(c)
    return uniq


# ----------------------------------------------------------------------------
# repository state and checking
# ----------------------------------------------------------------------------
class RepoState:
    """Tree of one snapshot plus parsed manifests."""

    def __init__(self, paths, manifest_text):
        self.files = set(paths)
        self.dirs = set()
        self.basenames = set()
        for p in paths:
            parts = p.split("/")
            self.basenames.add(parts[-1])
            for k in range(1, len(parts)):
                self.dirs.add("/".join(parts[:k]))
        self.dirbase = {d.rsplit("/", 1)[-1] for d in self.dirs}
        self.all = self.files | self.dirs
        self.manifest_text = manifest_text  # path -> text
        self._scripts = None
        self._targets = None
        self._jsdeps = None
        self._suffix = None

    def suffix_index(self):
        if self._suffix is None:
            idx = set()
            for p in self.all:
                parts = p.split("/")
                for k in range(1, len(parts)):
                    idx.add("/".join(parts[k:]))
            self._suffix = idx
        return self._suffix

    def path_ok(self, target, strict=False):
        isdir = target.endswith("/")
        t = target.rstrip("/")
        if "*" in t:
            rx = glob_regex(t)
            pool = self.all
            if any(rx.fullmatch(p) for p in pool):
                return True
            if strict:
                return False
            rx2 = glob_regex("**/" + t)
            return any(rx2.fullmatch(p) for p in pool)
        pool = self.dirs if isdir else self.all
        if t in pool:
            return True
        if strict:
            return False
        if "/" not in t:
            return t in (self.dirbase if isdir else (self.basenames | self.dirbase))
        return t in self.suffix_index() and (not isdir or any(d.endswith("/" + t) for d in self.dirs))

    def scripts(self):
        if self._scripts is None:
            s, deps = set(), set()
            for p, txt in self.manifest_text.items():
                if p.rsplit("/", 1)[-1] == "package.json":
                    try:
                        j = json.loads(txt)
                    except Exception:
                        continue
                    if isinstance(j, dict):
                        if isinstance(j.get("scripts"), dict):
                            s |= set(j["scripts"].keys())
                        for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                            if isinstance(j.get(k), dict):
                                deps |= set(j[k].keys())
            self._scripts, self._jsdeps = s, deps
        return self._scripts

    def targets(self, sub):
        if self._targets is None:
            mk, js, tk = set(), set(), set()
            for p, txt in self.manifest_text.items():
                b = p.rsplit("/", 1)[-1]
                if b in ("Makefile", "makefile", "GNUmakefile") or b.endswith(".mk"):
                    for m in re.finditer(r"^([A-Za-z0-9_.\-/ %$(){}]+?)\s*:(?!=)", txt, re.M):
                        for t in m.group(1).split():
                            mk.add(t)
                    for m in re.finditer(r"^\.PHONY\s*:\s*(.+)$", txt, re.M):
                        mk |= set(m.group(1).split())
                elif b.lower() in ("justfile", ".justfile") or b.endswith(".just"):
                    for m in re.finditer(r"^@?([A-Za-z0-9_\-]+)(?:\s+[^:=\n]*)?:(?!=)", txt, re.M):
                        js.add(m.group(1))
                    for m in re.finditer(r"^alias\s+([A-Za-z0-9_\-]+)\s*:=", txt, re.M):
                        js.add(m.group(1))
                elif b.lower().startswith("taskfile"):
                    for m in re.finditer(r"^\s{2,4}([A-Za-z0-9_:.\-]+):\s*$", txt, re.M):
                        tk.add(m.group(1))
            self._targets = {"make": mk, "just": js, "task": tk}
        return self._targets[sub]

    def manifest_ok(self, tool):
        for pat in MANIFEST_NEEDS.get(tool, []):
            if "*" in pat:
                if any(fnmatch.fnmatchcase(b, pat) for b in self.basenames):
                    return True
            elif pat in self.basenames:
                return True
        return False

    def dep_ok(self, tool, sub):
        if sub == "js":
            self.scripts()
            names = JS_PKG.get(tool, [tool])
            if any(n in self._jsdeps for n in names):
                return True
            # declared through a script body or a config file
            for p, txt in self.manifest_text.items():
                if p.endswith("package.json") and re.search(r"[\"/ ]" + re.escape(tool) + r"[\" @/]", txt):
                    return True
            return any(b.startswith((tool + ".config", "." + tool + "rc", tool + ".json")) for b in self.basenames)
        for c in PY_CONFIG.get(tool, []):
            if c in self.basenames:
                return True
        rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(tool).replace(r"\-", "[-_]") + r"(?![A-Za-z0-9])", re.I)
        for p, txt in self.manifest_text.items():
            b = p.rsplit("/", 1)[-1]
            if b == "package.json" or b.endswith(".mk") and False:
                continue
            if rx.search(txt):
                return True
        return False

    def check(self, c, strict=False):
        if c.kind == "path":
            return self.path_ok(c.target, strict)
        if c.kind == "script":
            return c.target in self.scripts()
        if c.kind == "target":
            ts = self.targets(c.sub)
            if c.target in ts:
                return True
            if c.sub == "make":  # pattern rules
                return any("%" in t and re.fullmatch(re.escape(t).replace("%", ".+"), c.target) for t in ts)
            if c.sub == "task":
                return c.target.split(":")[-1] in ts
            return False
        if c.kind == "manifest":
            return self.manifest_ok(c.target)
        if c.kind == "dep":
            return self.dep_ok(c.target, c.sub)
        raise ValueError(c.kind)


def glob_regex(g):
    out, i = "", 0
    while i < len(g):
        if g.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif g.startswith("**", i):
            out += ".*"
            i += 2
        elif g[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(g[i])
            i += 1
    return re.compile(out)


MANIFEST_BASENAMES = {"package.json", "Makefile", "makefile", "GNUmakefile", "justfile", "Justfile", ".justfile",
                      "Taskfile.yml", "Taskfile.yaml", "taskfile.yml", "taskfile.yaml", "pyproject.toml", "setup.cfg",
                      "setup.py", "tox.ini", "Pipfile", ".pre-commit-config.yaml", "noxfile.py", "environment.yml",
                      "uv.lock.NO", "hatch.toml"}


def is_manifest(path):
    parts = path.split("/")
    if "node_modules" in parts or "vendor" in parts or "third_party" in parts:
        return False
    b = parts[-1]
    depth = len(parts) - 1
    if b == "package.json":
        return depth <= 3
    if b in MANIFEST_BASENAMES or b.endswith(".mk") or (b.startswith("requirements") and b.endswith(".txt")) or b.endswith(".just"):
        return depth <= 2
    if depth == 1 and parts[0] == "requirements" and b.endswith(".txt"):
        return True
    return False


if __name__ == "__main__":
    import sys
    for c in compile_text(open(sys.argv[1]).read()):
        print(f"{c.line:4d} {c.kind:8s} {c.sub:11s} {c.target}")

#!/usr/bin/env bash
# Validate the dataminr-skills marketplace without needing the `claude` CLI.
# Usage: ./validate-skills.sh [--strict] [--json]
#   --strict  treat warnings as failures
#   --json    print findings as JSON (for CI)
# Exit code = number of errors (plus warnings with --strict). 0 means pass.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 - "$@" <<'PY'
import json, os, re, sys, glob

strict = "--strict" in sys.argv
as_json = "--json" in sys.argv
errors, warnings = [], []
err = lambda m: errors.append(m)
warn = lambda m: warnings.append(m)

def frontmatter(path):
    """Minimal YAML frontmatter reader: `key: value`, quoted values, and `>`/`|` blocks."""
    lines = open(path, encoding="utf-8").read().split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return None
    fm, i, body = {}, 1, lines[1:end]
    i = 0
    while i < len(body):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", body[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", "|", ">-", "|-"):
            parts = []
            i += 1
            while i < len(body) and (body[i].startswith(" ") or body[i].strip() == ""):
                parts.append(body[i].strip())
                i += 1
            val = (" " if val.startswith(">") else "\n").join(p for p in parts if p)
        else:
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            i += 1
        fm[key] = val
    return fm

# --- marketplace ---------------------------------------------------------
market = {}
try:
    market = json.load(open(".claude-plugin/marketplace.json"))
except Exception as e:
    err(f"marketplace.json: cannot parse ({e})")
listed = {}
for p in market.get("plugins", []):
    listed[p.get("name")] = p
    src = p.get("source", "")
    if not os.path.isdir(src):
        err(f"marketplace.json: plugin '{p.get('name')}' source '{src}' does not exist")
    elif os.path.basename(src.rstrip("/")) != p.get("name"):
        err(f"marketplace.json: plugin '{p.get('name')}' source dir name differs ('{src}')")
    if not p.get("description"):
        err(f"marketplace.json: plugin '{p.get('name')}' has no description")

dirs = sorted(d for d in os.listdir("plugins") if os.path.isdir(f"plugins/{d}"))
for d in dirs:
    if d not in listed:
        err(f"plugins/{d}: not listed in marketplace.json")
for n in listed:
    if n not in dirs:
        err(f"marketplace.json: '{n}' has no plugins/{n} directory")

# --- VERSIONS.md ---------------------------------------------------------
versions_rows = {}
if os.path.isfile("VERSIONS.md"):
    for line in open("VERSIONS.md", encoding="utf-8"):
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(\d+\.\d+\.\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|", line)
        if m:
            versions_rows[m.group(1)] = m.group(2)
    changelog = open("VERSIONS.md", encoding="utf-8").read()
else:
    err("VERSIONS.md is missing")
    changelog = ""

# --- per plugin ----------------------------------------------------------
for d in dirs:
    base = f"plugins/{d}"
    pj = f"{base}/.claude-plugin/plugin.json"
    ver = None
    try:
        j = json.load(open(pj))
        if j.get("name") != d:
            err(f"{pj}: name '{j.get('name')}' does not match directory '{d}'")
        ver = j.get("version", "")
        if not re.fullmatch(r"\d+\.\d+\.\d+", ver or ""):
            err(f"{pj}: version '{ver}' is not semver")
        for k in ("description", "author"):
            if not j.get(k):
                err(f"{pj}: missing '{k}'")
    except FileNotFoundError:
        err(f"{pj}: missing")
    except Exception as e:
        err(f"{pj}: cannot parse ({e})")

    if ver and versions_rows.get(d) != ver:
        err(f"VERSIONS.md: '{d}' row is {versions_rows.get(d) or 'missing'} but plugin.json says {ver}")
    if ver and not re.search(rf"^###\s+{re.escape(d)}\s+{re.escape(ver)}\b", changelog, re.M):
        warn(f"VERSIONS.md: no changelog heading '### {d} {ver}'")

    skill_dirs = [s for s in glob.glob(f"{base}/skills/*") if os.path.isdir(s)]
    if not skill_dirs:
        err(f"{base}: no skills found under skills/")
    for s in skill_dirs:
        sname = os.path.basename(s)
        sk = f"{s}/SKILL.md"
        if not os.path.isfile(sk):
            err(f"{s}: SKILL.md missing")
            continue
        fm = frontmatter(sk)
        if fm is None:
            err(f"{sk}: frontmatter missing or unterminated")
            continue
        name = fm.get("name", "")
        if not name:
            err(f"{sk}: frontmatter 'name' missing")
        else:
            if name != sname:
                err(f"{sk}: name '{name}' does not match directory '{sname}'")
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
                err(f"{sk}: name '{name}' must be lowercase a-z0-9 with single hyphens, at most 64 chars")
        desc = fm.get("description", "")
        if not desc.strip():
            err(f"{sk}: frontmatter 'description' missing or empty")
        else:
            if len(desc) > 1024:
                err(f"{sk}: description is {len(desc)} chars (max 1024)")
            if not re.search(r"\b(use (this|when|whenever)|trigger|invoke|whenever)\b", desc, re.I):
                warn(f"{sk}: description has no trigger phrase (e.g. 'Use when ...')")
        n = sum(1 for _ in open(sk, encoding="utf-8"))
        if n > 500:
            warn(f"{sk}: {n} lines (over 500); move detail into references/")

# --- secrets, local paths and internal terms ------------------------------
# Optional local-only file `.leak-patterns` (gitignored): one regex per line for internal
# hostnames, instance names and the like. Matches are errors. Keep that file out of the repo.
leak = []
if os.path.isfile(".leak-patterns"):
    for l in open(".leak-patterns", encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            leak.append(re.compile(l, re.I))
key_re = re.compile(r"""(api[_-]?key|secret|token|password|TC_KEY)\s*[=:]\s*["']?[A-Za-z0-9/+_\-]{20,}""", re.I)
path_re = re.compile(r"(/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|/private/tmp/|C:\\Users\\)")
skip_dirs = ("/.git", "/node_modules", "/skill-backups", "/docs/show-and-tell")
for root, _, files in os.walk("."):
    if any(x in root for x in skip_dirs):
        continue
    for f in files:
        path = os.path.join(root, f)[2:]
        if f == ".leak-patterns" or path in ("validate-skills.sh", "scripts/export-public.sh"):
            continue
        if f.startswith(".env"):
            if f != ".env.example":
                err(f"{path}: env file inside the repo")
            continue
        try:
            txt = open(path, encoding="utf-8").read()
        except Exception:
            continue
        for ln, line in enumerate(txt.split("\n"), 1):
            if path.startswith("plugins/") and key_re.search(line) and "example" not in line.lower() and "<" not in line:
                err(f"{path}:{ln}: looks like a credential")
            if path_re.search(line):
                err(f"{path}:{ln}: contains a local absolute path")
            for rx in leak:
                if rx.search(line):
                    err(f"{path}:{ln}: matches an internal-term pattern from .leak-patterns")
                    break

# --- report --------------------------------------------------------------
failed = len(errors) + (len(warnings) if strict else 0)
if as_json:
    print(json.dumps({"errors": errors, "warnings": warnings, "failed": failed}, indent=2))
else:
    for m in errors:
        print(f"ERROR  {m}")
    for m in warnings:
        print(f"WARN   {m}")
    print(f"\n{len(dirs)} plugins checked: {len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(min(failed, 125))
PY

---
name: playbook-explorer
description: Retrieves, explains, and audits ThreatConnect/TIP Playbooks given a playbook id, groupXid, or name. Resolves the id (v3 API lookup), downloads the full job definition (v2 API — v3 cannot return a single playbook's full definition), and produces a structured summary of the trigger, the job graph, which apps are used (LLM/agent prompts, TQL, JMESPath, Template Builder/FTL, branches, loops, Cache Store), and the TQL/JMESPath patterns in use. Also reviews a playbook against a growing checklist of confirmed best practices (JSON robustness, TQL hygiene, FTL null-safety, architecture) and flags what's missing or worth improving, with concrete fixes. Can also diff/compare two playbooks to produce a migration list. Use this whenever the user gives a playbook id/xid/name and asks to pull down, look at, review, audit, download, debug, understand, compare, migrate changes between, or improve a ThreatConnect playbook, or asks what's missing or could be better about one — even without naming this skill or "ThreatConnect."
---

<!-- CANONICAL SOURCE: the dataminr-skills repo, plugins/playbooks/skills/playbook-explorer/ . Edit only this file; ~/.claude/skills/playbook-explorer is a symlink to it. If you find another copy of this skill anywhere else, do not edit it: tell the user. -->

# TC Playbook Explorer

Retrieves a ThreatConnect Playbook's full definition and explains its structure — the trigger, the job graph, what each job's app type actually does, and the patterns (TQL, JMESPath, prompts) it uses. Built from real sessions resolving and reading actual playbooks; see `references/gotchas.md` for confirmed traps to avoid re-discovering.

## When to use this

Any time the user:
- Gives a playbook id, groupXid (short alphanumeric string), or name and asks to see/review/understand/debug it
- Asks "what does this playbook do" / "why is this playbook doing X" / "pull down the playbook and tell me about it"
- Wants to compare two playbooks, or check whether a specific pattern (a prompt, a TQL filter, a branch) exists in one

## What you need before starting

1. **The target instance's base URL** (e.g. `https://<instance>.threatconnect.com`). If not given, check the project for a `.env` file or prior conversation context before asking.
2. **A credential.** Look for a `.env` file (commonly in the project root) containing `TC_KEY=...`. If none exists, ask the user for one rather than guessing — never fabricate or reuse a credential from a different instance.
3. **The identifier** — numeric id, groupXid, or a name/partial name to search by.

If the session also has `mcp__threatconnect__*` MCP tools available, **do not assume they point at the same instance** as the one holding the playbook you want — see the MCP instance-mismatch note in `references/gotchas.md`. This skill's direct-API approach is instance-explicit by design; use it whenever the target instance isn't confirmed to match whatever the MCP tools are connected to.

**A project can have several instance-specific credential files** (e.g. `.env_instanceA`, `.env_instanceB`, `.env_instanceC`, alongside a bare `.env`) and/or several similarly-named playbooks across different instances — check for this rather than assuming one `.env`/one playbook xid is "the" target for a loosely-named reference like "the POC version." If a re-fetch ever shows no expected changes after work was supposedly done, that's a signal to stop and re-confirm the exact xid and instance rather than assuming continuity with an earlier fetch in the same session — see `references/gotchas.md`.

## Step 1 — Fetch the playbook

Use the bundled script (in this skill's own `scripts/` directory, alongside this file) rather than hand-writing the curl calls — it already handles id/groupXid/name resolution and the v3→v2 handoff:

```bash
bash scripts/fetch_playbook.sh \
  <base_url> <path/to/.env> <identifier> [out_dir]
```

- `<identifier>` can be a numeric id, an 8-12 char groupXid, or a name/partial name (the script detects which and resolves accordingly; a name search that matches more than one playbook will list the candidates instead of guessing).
- `[out_dir]` defaults to `./playbook-export` — pass an explicit path if the project has a convention for where these live (check for an existing `reference/playbook-export/`-style directory first).
- The script prints the saved file's path on stdout. If it exits non-zero, read its stderr output — it reports exactly what went wrong (ambiguous name match, v2 response that didn't look like a playbook, missing `TC_KEY`, etc.) rather than failing silently.

## Step 2 — Get oriented

Run the summarizer on the saved file before reading anything in full — it's cheap and gives you the shape of the whole playbook (trigger, job counts by app type, connection counts) before you spend context on any individual job's full prompt or TQL:

```bash
python3 scripts/summarize_playbook.py <saved_file.json>
```

Read `references/app_type_cheatsheet.md` now if you haven't already this session — it tells you which `jobParameterList` params actually matter per app type (a Base Agent job's `systemPrompt`, a TCPB API job's `params.tql`, etc.), so you don't waste effort reading irrelevant boilerplate params.

## Step 3 — Go deeper on what the user actually asked about

The summarizer's output tells you *what exists*; it doesn't interpret it. For the specific thing the user asked about:
- **A prompt/behavior question** → find the relevant Base Agent job by name in the summary, then read its full `jobParameterList` (via `python3 -c "import json; ..."` or `jq`) to get the actual `systemPrompt`/`userPrompt`.
- **A query/filtering question** → find the relevant `TCPB - ThreatConnect API v3` job, read its `params` (itself a JSON string — parse it), and resolve every `#App:...`/`#Global:...` reference inside the `tql` value by finding that job's own output to reconstruct the full expression that actually runs.
- **A "how does data flow" question** → use `playbookConnectionList` to trace `sourceJobId`→`targetJobId` edges, cross-referencing job ids against the summary's job list. Watch for `If/Else` branches and "Copy of X"-style duplicate jobs — see `references/gotchas.md`.
- **A branch/loop question** → look for `If / Else`, `Iterator`, and `Cache Store` app types specifically (don't assume a playbook is a flat static pipeline — see `references/gotchas.md`'s branching/loop note).

## Step 4 — Present findings in the user's terms, not a JSON dump

Structure the answer around what the user asked, typically:
- **Trigger & inputs** — what the playbook expects to receive and what it returns
- **Pipeline stages in execution order** — named in terms of what they do, not just job names (e.g. "resolves linked groups, then fetches six categories of associated intel in parallel")
- **Key prompts/queries worth knowing about**, quoted or closely paraphrased where the user's question is actually about behavior, not just structure
- **Anything surprising** — branches, loops, duplicate-looking jobs, inconsistent `fields=` usage, missing instructions — flagged explicitly rather than silently noted

Cite job ids and names so the user can cross-reference in the TC Designer UI directly (most instances expose a `groupWebLink` in the playbook metadata, e.g. `https://<instance>/#/playbooks/designer/<groupXid>` — surface that link too when presenting the summary, it's usually the fastest way for the user to jump straight to the Designer view of what you just described).

## Reviewing a playbook against best practices

Distinct from Steps 1-4 above, which describe/explain a playbook — this is for when the user explicitly asks for a **review, audit, improvement suggestions, or "is this configured well"** rather than just an explanation. Don't run this pass unprompted on a plain "what does this playbook do" ask; it's a deliberate, heavier mode, not the default.

`references/best_practices.md` is a **living checklist** (expected to keep growing across sessions, not a finished spec) of confirmed failure modes and the patterns that prevent them, organized by area: JSON-generation robustness (`JSON-1`..`JSON-6`), TQL/fetch hygiene (`TQL-1`..`TQL-3`), FTL/Template Builder robustness (`FTL-1`..`FTL-4`), and architecture/hygiene (`ARCH-1`..`ARCH-5`), trigger-payload handling (`PAY-1`..`PAY-4`), multi-step LLM pipelines (`LLM-1`..`LLM-4`), and report-template layout (`FTL-5`). Read it before starting a review.

Apply it systematically, not by spot-checking whatever catches your eye:
- For every `Base Agent` job: check it against `JSON-1` through `JSON-7`.
- For every fetch (`TCPB - ThreatConnect API v3`) job: check it against `TQL-1` through `TQL-3`.
- For every `Template Builder` job: check it against `FTL-1` through `FTL-4`.
- For every JMESPath job that emits plain strings reused downstream: check `JMES-4` (`strip_quotes`).
- For the JMESPath job that reads the trigger payload: check `PAY-1` through `PAY-4`, and run the payload contract check below.
- For any playbook with more than one Base Agent in a chain: check `LLM-1` through `LLM-4` and `LLM-7`.
- Across the whole job graph: check `ARCH-1` through `ARCH-5`.

Report findings grouped by category (not job-by-job, which buries the pattern), each marked present/missing/partial, naming the specific job(s) involved, and — for anything missing — the concrete fix from `best_practices.md` (most items include ready-to-use prompt/code text, not just a description of the problem). Don't pad the report with items that are fine; a clean "no issues found for X" per category is a legitimate and useful result. Treat this checklist as a floor, not a ceiling — if something looks wrong that isn't on the list yet, say so and suggest it as a new item worth adding to `best_practices.md`, rather than staying silent because it isn't a named check yet.

## Comparing or migrating changes between two playbooks

A common real task: a user has made changes to one playbook (often a "parallel"/test version) and wants to know what needs porting into a different one (a separate xid, sometimes on a different instance entirely — resolve each one's base URL/credential independently, don't assume they share an instance). Fetch both with Step 1, then use the bundled comparison script rather than eyeballing two large JSON files or writing a raw diff by hand — a naive diff drowns in noise from internal job-id references that legitimately differ between any two playbooks:

```bash
python3 scripts/diff_playbooks.py <playbook_a.json> <playbook_b.json> [job_name ...]
```

It filters out job-id-reference-only differences automatically (`#App:`, `#Global:` and `#Trigger:` ids) and reports genuine content diffs for ALL params of every job (prompts, expressions, Merge `output_array`, Logger `log_message`, fetch `params`, ...), plus a by-name comparison of the connection graph and a closing `SUMMARY` listing every changed job. Read the SUMMARY: a job missing from it genuinely did not change (an earlier version only inspected a short allow-list of params and silently skipped Merge/Logger jobs). Pass specific job names (e.g. the ones the user says they changed) to narrow the comparison rather than diffing every job blind. Treat playbook A as the baseline (`-` side) and B as the `+` side, and **double check which direction a surfaced diff actually goes** before reporting it to the user — it's easy to misread a unified diff's `-`/`+` sides quickly and report a finding backwards (confirmed mistake in a real session). When presenting the result, separate confirmed content differences from things that turn out to be pure formatting/whitespace, and flag anything that looks like leftover/abandoned work (e.g. dead CSS from a feature that was supposed to be reverted) rather than silently including or excluding it from a porting list.

It compares scope variables (where report/FTL templates and shared prompts often live) as well as job params; changes in a template-only scope variable used to be invisible to it.

## Checking a trigger payload against the playbook that reads it

Use when a run fails in the first extract job after a trigger, or when someone says "the UI now sends different JSON". Get the failing payload (the user can paste it; the Designer execution log shows the trigger output; if you really need it and cannot get it from the user, the trigger step's outputs can be read via the internal execution API, see `playbook-builder/references/execution_logs.md`), then:

```bash
python3 scripts/payload_contract_check.py <playbook.json> '<payload json>' [--job "Extract Report Config"]
```

It lists the keys each trigger-reading JMESPath job expects, which are missing from the payload, and flags each missing read as guarded (`key || default`) or UNGUARDED, noting whether it will raise (`join`/`length`/`in` on null) or silently produce the text "null" (`to_string`). It is a heuristic reader, not a JMESPath engine: confirm the flagged expressions by eye. Present the result as a short table (missing field / expressions that read it / effect), separate real failures from harmless defaults, and note any value that merely looks different (a renamed label). Then hand the fix to `playbook-builder` (make every payload read tolerant; see PAY-1..PAY-4).

## Testing a JMESPath expression offline before it goes into a playbook

Use when you write or change an expression for a JMESPath job (a shaper, a config extractor, a consolidator) and want to know it is well-formed and null-safe against REAL data without a push or a live run. Save a sample of the job's input (for a fetch-fed shaper, the raw response of the same `GET` the fetch job makes; for a trigger-fed job, a real payload), then:

```bash
python3 scripts/jmespath_local_test.py @expr.txt sample.json --sub 'rpt.assoc_groups=true'
```

`--sub name=value` replaces a ThreatConnect variable reference (`#App:<id>:rpt.assoc_groups!String`) with a literal; any reference left unreplaced stops the run with a list. It runs the standard JMESPath engine plus APPROXIMATE stubs of TC's custom functions (`regex`, `ternary`, `in`, `compact`, `flatten_list`, `group_by`, `include_keys`) and prints a note whenever a stub was used. Treat a pass as "well-formed and handles this data", not as proof the real job accepts it, and confirm anything non-trivial in a disposable sandbox playbook (see `playbook-builder`). The sample must include every record shape the job will meet; a null-field crash only shows up on the shapes that lack the field (see JMES-2). It needs the `jmespath` package; in a locked-down Python use a venv.

## Writing a hand-off brief for someone else's Claude Code session

When another engineer will load the playbook into their own session (to debug the viewer that renders its output, extend it, or review it), do not just send the JSON. Follow `references/handoff_brief_template.md`: one verified markdown file covering what the playbook does, its modes, the pipeline by job name, where its output comes from and what other layers add, the open problem with an experiment-by-experiment evidence table, known issues owned by others, and a suggested first prompt. Re-fetch first so the brief describes the current version, mark anything unverified, and never include credentials.


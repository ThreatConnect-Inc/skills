---
name: playbook-builder
description: Builds, updates, and live-tests ThreatConnect/TIP Playbooks from an LLM by editing the playbook's JSON definition, pushing it back to the instance (with user confirmation, local backups, a change log, and easy revert), then activating it and calling its webhook to validate the output. Use whenever the user wants to create, modify, update, tweak, fix, test, or revert a ThreatConnect playbook (e.g. change an agent's system prompt, edit a TQL query, adjust model settings, add or rewire jobs, "try it and see what it returns") — even if they don't name this skill. Pairs with playbook-explorer for reading, validating, and explaining the playbook before and after changes.
---

<!-- CANONICAL SOURCE: the dataminr-skills repo, plugins/playbooks/skills/playbook-builder/ . Edit only this file; ~/.claude/skills/playbook-builder is a symlink to it. If you find another copy of this skill anywhere else, do not edit it: tell the user. -->

# TC Playbook Builder

Pattern: **download -> edit JSON -> validate -> confirm with user -> backup + push -> activate -> webhook test -> review output -> deactivate -> explain.** Writes hit a live, shared instance, so every step that protects the user is mandatory, not optional.

Scripts (all in this skill's `scripts/`; none print `TC_KEY`):
| script | purpose |
|---|---|
| `push_playbook.sh` | backup live copy, diff, push edited JSON as a new draft, log to CHANGELOG (dry run unless `--yes`) |
| `playbook_ctl.sh` | `status` / `activate [draftId]` / `deactivate`; prints version, status and the **current** webhook endpoint |
| `test_webhook.sh` | call the current webhook endpoint (optional `--query`/`--body`), fail on non-2xx, save the response beside the backups |

Fetching/reading uses `playbook-explorer`'s `scripts/fetch_playbook.sh`. Details of API behavior: `references/api_notes.md`.

## The mental model (read this first)

- **groupXid is the identity; numeric ids are per-version.** Every push (POST) creates a **new Draft version with a new, unpredictable numeric id**, never overwriting anything — including when you POST to a draft id.
- **groupXid lookups (v3 TQL, v2 list, `GET /api/v2/playbooks/<groupXid>`) return only the *published* version.** A draft is reachable only by its draft id, which appears in the push output / `CHANGELOG.md`.
- **Activating a draft id promotes it** to published (minor version bump, e.g. 5.0 -> 5.1; re-activating bumps again) — so "publish" = activate the draft. Deactivating leaves it published but Inactive.
- **The webhook endpoint UUID can change between versions.** Never reuse an old one.

## Step 1 — Connect to the right instance

- **Direct API (default, instance-explicit).** Needs a base URL and a `TC_KEY` env file. Env files are per instance (`.env_instanceA`, `.env_instanceB`, `.env_instanceC`...) and contain only `TC_KEY` — not the URL. Look in the project or the working directory the user names; never fabricate or reuse a key from another instance. If the URL isn't given, ask the user for it; do not guess an instance.
- **MCP (`mcp__threatconnect__*`) is discovery-only for playbooks.** It is bound to one instance (no per-call override), lists playbooks as read-only, `tc_list` returns metadata only, and `tc_get` on a playbook returns 405. Use it to browse; do all full reads and all writes via direct API.
- Never print `TC_KEY`; redact when showing env contents.

## Step 2 — Find and confirm the playbook

Resolve by name, groupXid, or numeric id (`playbook-explorer` `fetch_playbook.sh`). **Confirm with the user before editing**: state instance, playbook name, groupXid, current version, and say whether you fetched the published version or a specific draft; ask "is this the one?" — especially if a name search returns several matches or the user was loose ("the POC version"). If the user says they edited the playbook in the Designer but a fetch shows the old version, it is probably an unpromoted draft: ask them to activate it or send the Designer URL (the numeric id is in it).

## Step 3 — Edit the JSON locally

Work on a copy of the fetched file; never edit the only copy. Make the smallest change that does the job; leave every other field untouched. Edit points:
- Agent prompts: `jobList[].jobParameterList[]` where `appCatalogItemParameter.paramName` is `systemPrompt` / `userPrompt` (match on paramName, not position).
- Set Variable values: the `variable_mapping` param is a JSON **string** (`[{"key":...,"value":...}]`) — parse, edit, re-serialize compactly.
- Model settings: `jobList[].languageModelConfiguration`.
- Graph: `jobList`, `playbookConnectionList`, `playbookTriggerList`. Adding/rewiring jobs is higher risk — see `playbook-explorer/references/app_type_cheatsheet.md` and copy the shape of an existing job of that type. `#App:<jobId>:<var>!String` references must use real job ids in the same playbook.
- Always **start from the latest version you intend to build on** (re-fetch right before editing; if you're iterating on a draft, fetch it by draft id). Editing a stale copy silently drops the user's Designer changes.

## Dev playbooks run at DEBUG/TRACE

**Every playbook under development or test must have top-level `logLevel` set to `DEBUG` or `TRACE`** (valid values: TRACE, DEBUG, INFO, WARN, ERROR). At `WARN` a manual review of the execution shows almost nothing. Only move to `INFO`/`WARN` when promoting back to production, for log reduction — and tell the user when you do. Set it when creating a playbook and check it on every edit; `push_playbook.sh` prints a warning if the pushed definition isn't DEBUG/TRACE. Note a playbook can silently be at a different level than you expect (versions differ), so read the field from the version you are editing rather than assuming.

## Step 4 — Validate before pushing

1. Run `playbook-explorer`'s `summarize_playbook.py` on the edited file and `diff_playbooks.py <live> <edited>` to confirm only the intended fields differ. Read the closing `SUMMARY` block: it lists every job whose params changed and the connection-graph changes (by job name), so a job you did not mean to touch, or one you meant to change but did not, is visible at a glance. (It compares ALL params of every job; an earlier version only checked prompts, templates and expressions and silently skipped Merge/Logger/If-Else jobs.)
   For a new or edited JMESPath expression, also run it offline against a real sample of its input with `playbook-explorer`'s `scripts/jmespath_local_test.py` (well-formed? null-safe on every record shape?), then confirm anything non-trivial in a sandbox playbook (the TC custom functions are only approximated offline).
2. Check against `playbook-explorer/references/best_practices.md` and flag anything relevant.
3. Show the user the diff in plain terms and get an explicit yes (unless they've already directed the exact change, as with "set X to Y and test it").

## Step 5 — Back up and push

```bash
# dry run: backs up the live copy and shows the diff, pushes nothing
bash scripts/push_playbook.sh <base_url> <env_file> <edited.json> <backup_root> --note "why"
# after approval:
bash scripts/push_playbook.sh <base_url> <env_file> <edited.json> <backup_root> --yes --note "why"
```

It resolves the live id from groupXid, saves `<backup_root>/<groupXid>/<UTC ts>_before.json`, POSTs to `/api/v2/playbooks/<id>` (PUT is 405), re-fetches `_after.json`, and appends version / old id -> **new draft id** to `CHANGELOG.md`. Use a persistent project folder for `<backup_root>` (e.g. `./playbook-backups`). Note `_before` is the *published* version; if you're iterating on drafts that differ from it, the diff will show that too — read it.

**The printed diff is a raw text diff, not a semantic one — don't panic at large removed-then-readded blocks.** Appending a single new connection to the end of `playbookConnectionList` produced a diff showing a dozen-plus unrelated connections as removed (confirmed on instance C, 2026-10-20): pure list-reordering/formatting noise from the text-diff algorithm, not real content loss. Before concluding anything was actually dropped, verify with a semantic comparison — e.g. build a `set()` of `(type, sourceJobId, targetJobId, sourceTriggerId, targetTriggerId)` tuples from both the `_before.json` and your edited file and diff the sets, not the raw JSON text. `playbook-explorer`'s `diff_playbooks.py` already normalizes job-id-reference noise for *parameter* values, but connection-list reordering is a separate case worth checking by hand if the printed diff looks alarming.

## Step 6 — Activate and test (webhook-triggered playbooks)

The standard live validation loop (worked example: instance A `<id-A>` "Test AI Update"):

```bash
bash scripts/playbook_ctl.sh <base_url> <env> status <groupXid>                 # should be Inactive before you start
# ...edit + push (Steps 3-5) -> note the new draft id...
bash scripts/playbook_ctl.sh <base_url> <env> activate <groupXid> <draftId>      # promotes the draft
bash scripts/test_webhook.sh <base_url> <env> <groupXid> <backup_root> --label "what I'm testing"
bash scripts/playbook_ctl.sh <base_url> <env> deactivate <groupXid>              # when finished
```

- **State the expectation before calling** (e.g. "30-day request, today 2026-10-13 -> expect 2026-09-13"), then compare. Check the HTTP status, not only the body: an empty body with 404 means a stale endpoint, not "empty output" (`test_webhook.sh` fails loudly and always resolves the current endpoint).
- Only activate/call playbooks the user has said are test ones, and only when asked or clearly part of the requested test; **deactivate afterwards** and tell the user the final state. Active playbooks with Timer/Mailbox/webhook triggers can do real work or fire on a schedule — flag odd trigger settings you notice (e.g. a webhook trigger with `scheduleType: Daily`).
- Responses are saved as `webhook_<ts>_v<version>.txt` beside the backups, so outputs can be compared across versions.

**Example shape** (what a good test harness looks like): WebHook Trigger -> `TCPB - SetVariable v1.0` (`variable_mapping` = `[{"key":"user.request","value":"<test input>"}]`, output var `user.request`) -> Base Agent (`userPrompt` references `#App:<setVariableJobId>:user.request!String` and `#Global:0:gbl.timestamp.iso!String`; output var `agent.out`) -> back to the trigger, whose `httpResponseBody` is `#App:<agentJobId>:agent.out!String` (`httpResponseCode` `200`, `httpResponseHeader` `[{"key":"content-type","value":"text/plain"}]`). The return edge is a Pass connection from the last job to the trigger (`targetTriggerId`, `isCircularOnTarget: true`).

**Test-data styles** (hardcoded Set Variable vs. data passed in on each webhook call, so no push is needed per input):

- *Hardcoded:* a Set Variable step as in the example above. Cheap to read; every input change needs a push.
- *Query parameters* (worked example: instance A `<id-A>` v5.3). Call `<endpoint>?query=<text>` (`test_webhook.sh --query "query=..."`). Wiring: WebHook Trigger -> **`TCPB - KeyValue Operations v1`** ("Parse Query Params") -> Base Agent -> back to the trigger. The KeyValue Operations job has `tc_action` = `Value Lookup`, `input_array` = `#Trigger:<triggerId>:trg.http.queryparam!KeyValueArray`, `fail_on_no_results` = `true`, and `column_mapping_lookup` = `[{"key":"user.query","value":"query"}]` (output variable name -> query-param name; the output variable is created by the mapping, so the job's `outputVariables` can show `[]`). The agent's `userPrompt` then references `#App:<keyValueJobId>:user.query!String`. Pass URL-encoded text (`test_webhook.sh` auto-encodes raw spaces; pre-encode `&`, `#`, `+`, `%`) and **decode it after parsing** (e.g. with a decode step) before the agent sees it. Tested 2026-10-13 on v5.4: `?query=...past%2014%20days` -> `2026-09-29` (correct). Not yet verified whether a decode step is actually needed for the agent to read it correctly; the model coped with `%20` text here. **A missing `query` param returned HTTP 200 with an EMPTY body** (the failure is internal, not an HTTP error) — treat an empty 2xx body as a failed run, not as a pass.
- *POST body + JMESPath* (worked example: instance A `<id-A>` v5.5/5.6, tested 2026-10-13). Send `test_webhook.sh --body '{"query": "..."}'` (POSTs with `Content-Type: application/json`). Wiring: WebHook Trigger -> **`TCPB - JMESPath v2.0`** -> Base Agent -> back to the trigger. The JMESPath job has `json_data` = `#Trigger:<triggerId>:trg.http.body!String`, `strip_quotes` = `true`, and `string_expressions` = `[{"key":"user.query","value":"query"}]` (output variable name -> JMESPath expression; again the variable is created by the mapping, so `outputVariables` shows `[]`). The agent's `userPrompt` references `#App:<jmespathJobId>:user.query!String`. Results: `{"query":"...past 21 days"}` -> `2026-09-22` (correct); a query containing escaped quotes, `&`, an en dash and a date (`...since 2026-10-01 – thanks!`) -> `2026-10-01` (correct, so JSON escaping is handled with no decode step). **Missing key or `{}` body:** HTTP 200 but the agent receives an empty variable and replies with an apology/"no user request" string (not an empty body) — so with this wiring a bad request looks like a *successful* run with a nonsense answer. Always compare the output against the expected value; consider adding validation (If/Else on empty `user.query`) to a real playbook. For other body shapes, change only the JMESPath expression (see `jmespath-assistant`).
- **Which to choose:** query params for simple strings; JSON body for structured/multi-field test data (add one `string_expressions` entry per field) and anything with special characters.

**Trigger caching:** the trigger JSON always carries `cacheMinutes`/`cacheParams` even when "enable data caching" is OFF, so the values don't indicate caching. No on/off field has been identified in the JSON — ask the user. If it is on, repeat calls can return stale output (the default cache key ignores body and query params); turn it off or include the varying params while testing.

## Adding jobs and branches (worked example: instance A `<id-A>` v6.0/6.1, tested 2026-10-13)

Goal: reject a bad webhook request instead of letting the agent answer nonsense. Result: JMESPath -> **If / Else** -> (query present) Base Agent / (missing) Set Variable error message -> **Merge** -> trigger response.

How to add a job reliably:
1. **Copy a real job of that app type** as a template (from the live playbook, another export in the project, or `playbook-explorer`'s exports) — copy the whole object including `appCatalogItem`; change `id`, `name`, `locationLeft/Top` and only the params you need. Don't hand-write the `appCatalogItem`. App catalog ids copied from another instance's export were accepted.
2. Use any unique job ids in your edit and wire references (`#App:<id>:<var>!String`) to them. **On push the server renumbers the new jobs and rewrites every reference consistently** (job params and the trigger's `httpResponseBody`) — so after a push, re-read ids from `_after.json`, never from your edit file. (Trigger ids also change per version; `#Trigger:<id>:...` refs are rewritten too.)
3. Rebuild `playbookConnectionList` for the affected part of the graph: remove the old edges you're replacing, add new ones as `{"type": "Pass"|"Fail", "isCircularOnTarget": false, "sourceJobId": ..., "targetJobId": ...}`; an edge back to the trigger uses `"targetTriggerId"` and `"isCircularOnTarget": true`. Verify with `summarize_playbook.py` and by printing the edges before pushing.
4. **Every job that consumes another job's output via `#App:<id>:<var>!Type` needs an explicit connection edge FROM the producer TO the consumer, not just the variable-reference string** (confirmed on instance C, 2026-10-20, adding a new Base Agent job into an existing playbook that had no agent jobs before). Forgetting the producer -> consumer edge — i.e. only wiring the producer's upstream input, not its downstream output — fails `activate` with `Invalid Variable Reference in Parameter(s): Variable: #App:<id>:<var>!Type`, naming the *consuming* job as `rootId`. Two things made this confusing to diagnose: the new job's `outputVariables` field read back as `[]` after every push regardless of what was declared (renaming the output variable to match the convention every other Base Agent job on the instance uses, `agent.out`, did NOT fix it — `outputVariables` was still `[]` after that push too, and activation still failed identically). It turned out `outputVariables` wasn't the load-bearing field at all: adding the missing producer -> consumer connection edge fixed activation immediately, with `outputVariables` still showing `[]` in the stored JSON. Lesson: when `Invalid Variable Reference` fires on activate, check the connection graph between the two named jobs FIRST, before suspecting the output variable declaration or app catalog shape.

Shapes confirmed:
- **If / Else** (`appCatalogItem.id` 5): params `operand_1`, `operator` (only `equals` seen in existing playbooks), `operand_2`, `as_numeric` (`"false"`), `match_case`. **Condition TRUE = `Pass` edge, FALSE = `Fail` edge.**
- **Comparing to "empty":** don't compare against an empty/undefined variable (unresolved references reach downstream apps as placeholder text like `VARIABLE_NOT_...`). Instead make the upstream step produce a **sentinel default**: JMESPath expression `query || 'NO_QUERY'` (null, missing, and `""` are all falsy) and test `equals NO_QUERY`.
- **Merge** (`appCatalogItem.id` 19): `output_array` = `[{"key":"response.merged","value":"#App:<agentId>:agent.out!String#App:<errId>:error.message!String"}]` — a plain concatenation that works as a coalesce when only one branch runs; both branches connect into it, and the trigger's `httpResponseBody` references the Merge output (`#App:<mergeId>:response.merged!String`). Set the Merge job's `outputVariables` to declare `response.merged`.
- **Set Variable** (`TCPB - SetVariable v1.0`) for a fixed error message: `variable_mapping` JSON string, plus `outputVariables` declaring the variable.
- Limitation: the trigger has a single static `httpResponseCode` (`200`), so the error branch returns **HTTP 200 with an error message body** — check the body text, not the status, when testing error paths.

Test matrix that passed (all via `test_webhook.sh --body`): valid query -> correct date (twice, to confirm the valid path still works after the error path ran); `{"other":"x"}`, `{}`, and `{"query":""}` -> the error message. Always test both branches, and re-test the happy path after the error path.

## Debugging: build observability into the playbook first; read execution logs only when really needed

There is no documented execution-log API, but step statuses, exit messages, inputs, outputs and app logs can be read through the Designer's internal API using the user's signed-in browser session (see `references/execution_logs.md`). That route is slow and heavy, so use it only after the cheap signals fail. A failed run through the webhook otherwise shows up only as an empty body, a nonsense answer, or a wrong value, with no reason. So **make the playbook explain itself through the webhook response**:

- Give each failure/branch path its own **distinct, descriptive message** (a Set Variable or Logger on that branch, e.g. `ERROR[no-query]: body must be JSON like {"query": "..."}`, `ERROR[agent-empty]: agent returned nothing`), and route every branch into the **Merge** feeding the trigger's `httpResponseBody`, so the message from whichever path actually ran comes back to you. Prefix messages with a short path tag so you can tell which branch fired.
- Add checks where things can silently go wrong (empty/missing inputs, empty agent output, empty fetch results) and a branch for each, instead of letting bad data flow into the next step. Use the sentinel-default + If/Else pattern above.
- While developing, it's fine to return intermediate values too (e.g. include the parsed `user.query`, or a step's output, in the response alongside the result) to see what each step produced; strip that out before finalising if the user wants a clean output.
- When a test returns something unexpected or an empty body, don't guess: add a debug branch/output that exposes the suspect value, push, re-test, and narrow it down. Explain to the user what each message means.
- Remember the response code is fixed (200), so rely on the message text.

## Worked example 2: building a new data-driven playbook (threat hunt pack, instance A `ZZthp001x`, 2026-10-13)

Request: webhook `?groupId=<TC group id>` -> look up the group's IOCs and ATT&CK tags -> agent builds a threat hunt pack -> returned to the webhook. Built entirely by script (`references/example_build_playbook.py` — copies real job templates, sets params, wires connections, writes the JSON; paths in it are session-specific, reuse the technique). Flow: Parse Query Params (KeyValue Ops) -> Fetch Group -> Shape Group -> Fetch IOCs -> Shape IOCs -> Fetch ATT&CK Tags -> Shape TTPs -> If no data -> (Fail) agent / (Pass) error message -> Merge -> trigger.

What to reuse:
- **Fetch job** = `TCPB - ThreatConnect API v3`: params `http_method` (`GET`), `url` (`/v3/indicators`, `/v3/tags`, `/v3/groups/<id>`), `params` (JSON string array of `{"key","value"}`, e.g. `tql`, `resultLimit`, repeated `fields`), `fail_on_error`. Output `tc.api.content` (String, raw API JSON). Shape it with a JMESPath job (`data[*].{type: type, indicator: summary, ...}`), which also trims what the agent has to read. Copy the fetch job from another playbook export in the project (the report-agent exports have them); its app catalog entry was accepted on instance A.
- **TQL for associated intel (confirmed):** IOCs: `hasGroup(id = N OR hasGroup(id = N))` on `/v3/indicators` (the group plus its linked groups); ATT&CK tags: `hasGroup(id = N OR hasGroup(id = N)) AND techniqueId is not null` on `/v3/tags`. Check queries with direct API calls on candidate ids **before** building. Test-data lesson: on instance A, Intrusion Sets carry the ATT&CK tags and Events carry the IOCs, so a direct-only query found no group with both — the linked-group form is what made a useful test case (The Gentlemen ransomware group `<group-id>`: 21 techniques, 5 IOCs via linked groups).
- **"No data" check** without an extra variable: If/Else `operand_1` = two shaped outputs concatenated (`#App:<iocs>:shaped!String#App:<ttps>:shaped!String`) `equals` `[][]`. A nonexistent group id returned `ERROR[no-data]: group 999999999 (UNKNOWN) ...` — the group-name shape uses `data.name || 'UNKNOWN'` and the group fetch has `fail_on_error` `false` so a 404 doesn't kill the run.
- **Agent prompt for long outputs:** the first run was cut off mid-sentence at 8,000 `maxOutputTokens` (21 techniques x per-technique detail). Fixed by (a) putting the most important sections first and the long per-item section **last** so any truncation costs the least, (b) telling the model to be concise with a word budget and to group related items, (c) raising `languageModelConfiguration.maxOutputTokens` to 16000. Always check the *end* of a long output for truncation, not just the start.
- Webhook runs with an agent can take **1-3 minutes**; run `test_webhook.sh` in the background (it allows 300s) and read the saved file. macOS has no `timeout` command.

Gotchas hit while creating:
- On create, **omit `scheduleType`** from the trigger; `"None"` is rejected (`Job$ScheduleType` only accepts Daily/Advanced/Monthly/Weekly). The summarizer prints `None` for a missing key.
- The v2 create response can contain raw control characters: parse with `json.loads(s, strict=False)` or re-GET the playbook rather than trusting the response body.
- **Keep your template files in a persistent folder** (the project, e.g. next to `playbook-backups/`), not only in scratch: the scratchpad was wiped mid-session. If a template job is lost, old draft versions are still fetchable by id (`GET /api/v2/playbooks/<id>`; scan nearby ids) and `_after.json` backups hold every pushed version.
- Known weak spot: a **missing `groupId`** still returns HTTP 200 with an EMPTY body (KeyValue Ops `fail_on_no_results` = true halts the run silently). To make it observable, add a guard before the fetches (e.g. turn `fail_on_no_results` off and test for a sentinel) — not yet done.

## Writing TQL: consult `intel-lookup`, then verify against the target instance

Before writing any TQL for a fetch job, read the `intel-lookup` skill's references (`reference/tql_reference.md`, `object_field_reference.md`, `ioc_scoring_and_topic_queries.md`, `unified_object_queries.md`). That skill is MCP-oriented and its MCP connector may point at a different instance than your target (e.g. instance D vs instance A), so use it for **syntax and field knowledge**, then **verify every query with a direct API call on the target instance** (`GET /v3/<resource>?tql=...&resultLimit=...`) before putting it in a playbook. Findings applied in the threat-hunt-pack playbook (2026-10-13):
- **Score by ThreatAssess, not confidence/rating.** `confidence`/`rating` are unreliable. Request `fields=threatassess` (a bundle; `threatassessscore` is rejected) to get `threatAssessScore`, `calScore`, etc. back, and sort with the `sorting` param (`threatAssessScore DESC`, confirmed). In the playbook's `params` array these are separate entries: `{"key":"fields","value":"threatassess"}`, `{"key":"sorting","value":"threatAssessScore DESC"}`. Pass the score (and `calScore`, `source`, `lastModified`) through the JMESPath shape step. Typical meaning: `threatAssessScore` roughly 0-1000, ~700+ high; give the agent that scale so it doesn't call a 280 "high".
- **Don't hard-filter on a score threshold when the data may be sparse.** On instance A every IOC of the test group scored 280 (`calScore` 170), so `threatAssessScore >= 700` would return nothing. Sort and let the agent weigh, unless the user wants a cutoff. Do add `falsePositiveCount = 0`.
- **Inactive indicators:** the platform injects `indicatorActive = true` by default. For *lookups* ("have we seen this") override it with `(indicatorActive = false OR indicatorActive = true)`; for *hunting/sweeping* keep it active-only and say so explicitly (`indicatorActive = true`) — on instance A the override pulled in an inactive `example-victim.com` host, which would be a bad thing to sweep for.
- **ATT&CK tags:** `techniqueId is not null` on `/v3/tags` returns **MITRE ATLAS** tags too (IDs like `AML.T0049`) — they are real tag data, not hallucinations. Tell the agent that `AML.*` IDs are ATLAS (adversarial-ML), not ATT&CK. On this instance tags returned no `financialRisk`/`securityCoverage`/`active` values; `description` (MITRE text, long) is available by default but costs tokens.
- Other confirmed TQL quirks: use `typeName` not `type`, `summary` not `name` on groups/indicators; `NEQ` isn't valid (use `!=`/`NE`); `fields=` on tags rejects `description` (it's already returned).
- **One fetch for several bases: put the TQL function name in a variable instead of duplicating jobs per branch.** An agent that can report on groups OR indicators needs `hasGroup(id in (...))` for one and `hasIndicator(id in (...))` for the other around the same context fetches. Compute the function name once in the config-extract job (`ternary(objectType == 'Indicator', 'hasIndicator', 'hasGroup')`) and write the fetch TQL as `<ref>(id in (<ids>) ...)`. This keeps one set of fetch/shape jobs for every basis. `hasIndicator(...)` was confirmed on groups and tags endpoints by the playbook owner; verify each endpoint you use with a direct GET first, because TQL association functions are not valid on every resource. Store the selected ids once (a global variable set after a Merge job, which outputs whichever input exists) so every fetch reads the same list.
- Every field a downstream shaper reads must be in the fetch's `fields` (see TQL-4 in `playbook-explorer/references/best_practices.md`); `fields=insights` works on groups only, indicators reject it.

## Creating a playbook from scratch

`POST /api/v2/playbooks` with a full definition (e.g. an export from another instance) creates v1.0, Inactive. Change `name` and **`groupXid`** first (a fresh 9-char xid worked; reusing the source's would collide) and give test playbooks an obvious name ("ZZ ... - delete me"). Instance-specific ids in an export were accepted across instances. Then use the normal push/activate/test loop on it. On shared instances (a shared UAT instance has hundreds of others' playbooks) only touch playbooks you created.

## Disposable sandbox playbooks for isolated unit-testing (self-testing during development)

**When building or debugging anything non-trivial — a JMESPath expression, an unfamiliar app's exact parameter/output shape, a TQL escaping rule, a tricky job-to-job data-relay pattern — don't iterate inside the real target playbook.** Build (or reuse) a tiny, disposable, single-purpose webhook playbook instead: one or two jobs wired directly `Trigger -> job(s) -> Trigger`, with a hardcoded or webhook-supplied test input, nothing else. This is the single technique that unblocked the most difficult problems across this whole project (DataStore GET/POST shape, the Binary Operations Unicode defect, the Get Groups ID-vs-Entity distinction, the TQL backslash-escaping rule, several JMESPath edge cases) — confirmed consistently faster and far less error-prone than reasoning abstractly or debugging a failure that could be anywhere in a large production chain.

- **Naming/reuse convention:** name it obviously disposable (`ZZ <what it's testing> - delete me`), per the "Creating a playbook from scratch" section above. If the user already has a scratch playbook like this sitting around in the project (check first), reuse and repurpose it rather than creating a new one each time — swap its job(s)/params for whatever you're testing next; its whole value is being cheap to throw away and rebuild.
- **For a JMESPath expression:** first run it offline against a real saved sample with `playbook-explorer`'s `scripts/jmespath_local_test.py` (catches malformed syntax and null crashes in seconds; its stubs of the TC custom functions are approximate), then confirm in a sandbox: wire `Trigger -> TCPB - JMESPath v3.0 -> Trigger`, feed it either a hardcoded literal JSON (a `JSON Operations`/`Set Variable` job upstream, or just embed the sample JSON directly as the test payload via `test_webhook.sh --body`) shaped like the REAL data you'll eventually run it against, set `json_data` to that, and put the expression under test in `string_expressions`/`string_array_expressions`. Call the webhook, read the exact output. This is far more reliable than reasoning about JMESPath semantics (especially the TC-specific custom functions, or subtle string-literal escaping rules) in the abstract — see `playbook-explorer`'s gotchas for confirmed cases this caught (a silently-invalid `arr[*].(expr)` pattern, `map()` vs. bare-projection null-dropping).
- **For an unfamiliar or newer app's exact config shape:** when raw-API-pushed guesses at an app's parameters aren't working (confirmed failure modes: `outputVariables` silently stripped to `[]`, spurious "required field missing" from stale `layoutRequiredInputParams` — see `playbook-explorer/references/gotchas.md`), the fastest real unblock is to **ask the user to configure one job of that exact type directly in the Designer UI**, inside the same disposable sandbox playbook, then fetch it back as a working template to copy from. Trial-and-error against raw API pushes can burn many rounds on an app whose Designer-required shape isn't obvious from the job JSON alone; a single user-configured example settles it immediately.
- **For a data-relay/chaining question** (e.g. "does this param type accept this reference, does this corrupt binary content, does this app's output feed cleanly into that app's input"): build the smallest chain that isolates just the hop in question, with literal test data at the start and the response showing the end result directly — don't build the full multi-hop production chain first and then try to figure out which hop broke it.
- Push, activate, call via `test_webhook.sh` with the literal test payload, read the response, adjust, repeat — then deactivate when done, same as any other test playbook (see the Safety rules below and the Step 6 webhook loop above). Once the isolated test confirms the pattern works, port the confirmed-working job/expression into the real target playbook rather than rebuilding it there from scratch.
- **A sandbox test of a job that normally receives a large upstream context (another app's full raw output, not just a small literal) is only trustworthy if the sandbox feeds it that same real context — a hand-built stub can pass cleanly while the identical fix fails in production.** Confirmed TWICE in one campaign (instance C, Oct 2026): a prompt fix for a secondary LLM agent that normally reads a primary extractor's full raw output passed 3-for-3 in an isolated sandbox fed only a small manually-constructed stand-in, then produced the SAME failure as before once deployed and run against the real pipeline (which always passes the primary extractor's actual, much larger output). Report an isolated-sandbox pass on this kind of job as provisional, not confirmed, until a real end-to-end run backs it up — and when faithfully reproducing the upstream context by hand is impractical, run the real upstream app inside the sandbox too (e.g. `Trigger -> <the real upstream app> -> <job under test> -> Trigger`) instead of approximating its output.

## Reverting

Every push has a `_before.json`. To revert, push that file with `push_playbook.sh` exactly as above (it takes its own new backup first, so reverts are themselves revertible), then activate the new draft id if the reverted version should be live. `CHANGELOG.md` lists every push with version and draft ids.

## Safety rules

- Confirm target and change with the user before every write; approval for one change doesn't cover the next.
- **Never delete playbooks** (v2 `DELETE /api/v2/playbooks/<id or groupXid>` exists) — hard deletes are the user's action; give them the command or the Designer link.
- Be extra careful on instances that aren't clearly test/QA and on playbooks not declared disposable.
- Report failures verbatim. If the post-push or webhook check doesn't show the intended change, say so and offer revert — never report a pass without comparing against a stated expectation.

## Lessons from building a multi-prompt agent variant (applies to any multi-step agent; worked example: a report-agent variant, Oct 2026)

Worked example: a copy of an existing report agent (9 prompt jobs, 1 JMESPath job, 1 template stored as a scope variable) that gained a new output format, edited via one build script, pushed ~7 times, activated each time, tested through the Report UI. Keep the equivalents in your own project: a build script, a CHANGELOG, a backup folder, and a note of the instance each copy lives on.

### Make a variant instead of touching a playbook other people are testing
- Create a COPY: fresh 9-char `groupXid`, name suffix (e.g. " - operational reporting"), and ALSO suffix the **trigger name**, because UIs list agents by trigger name and the copies share chat trigger types. Set `logLevel` to DEBUG. Leave the original untouched and say so.
- A created copy is v1x.0 Inactive; the user may activate it themselves, which bumps the minor version (12.1 -> 12.2). Always re-fetch the LIVE copy before the next push and diff it against your last pushed `_after.json` (see below) so you never overwrite their Designer edits.

### Scripted, anchored edits beat ad hoc edits
- Write ONE build script in the project (not scratch) that loads a source export, applies every change through a helper `sub(text, old, new, label)` that **asserts the anchor occurs exactly once**, and writes the output file. A drifted source then fails loudly instead of silently half-applying, and the whole change set is reproducible and reviewable. Rebuild from the source each time rather than patching the output.
- Python quoting trap: prompt text full of `"`, `\` and `{}` is safest in triple-quoted strings; build patches in a file and run it (an inline heredoc with escaped quotes failed once and silently did nothing: always print a verification of every change after applying).
- Re-run `diff_playbooks.py` against the live copy and confirm ONLY the intended jobs differ. Note it normalizes `#App:`/`#Trigger:` ids and does NOT compare `playbookScopeVariables` (e.g. an FTL template stored as a scope variable); check those separately. `push_playbook.sh`'s dry-run diff is huge and noisy for the same reason (every id renumbers): pass `--brief` to print only the semantic summary (changed jobs and connection changes, via `playbook-explorer`'s `diff_playbooks.py`) instead of the raw text diff, or filter the output (`grep -E '^Pushed|_after'`).

### Pushing and activating reliably
- A push to an existing groupXid POSTs a new draft; the server renumbers ALL job/trigger/scope-variable ids and rewrites every `#App:`/`#Trigger:` reference consistently (also confirmed for edits that changed ids). Verify after pushing by re-fetching and checking that every `#App:<id>` resolves to a real job (a dangling ref that already existed in the source, e.g. in an unused job, will carry over harmlessly).
- Draft ids vary in shape (`1125899906…` and `2251799813…` both seen): never regex them by prefix. Parse the line `Pushed. version X, new id N` and pass N explicitly to `playbook_ctl.sh activate <groupXid> <N>`. (Activating with no id ended up on the newest draft once, but do not rely on that.)
- `push_playbook.sh` can run longer than a 120 s foreground tool timeout: run it in the background or with a long timeout, and wait for the "Pushed." line before activating.
- If the user has said "always activate after pushing" for a test copy, do it, confirm `status` shows the new version Active, and tell them the active version (activation bumps the minor version). Never extend that to other playbooks.

### Editing details that bit
- Jobs declare `outputVariables` explicitly (a JSON **string** on some jobs, a list on others): when you add a new output to a JMESPath job, append the declaration in the same shape, or downstream `#App:<id>:<var>` refs may not resolve.
- Params live at `jobParameterList[].appCatalogItemParameter.paramName` / `.value`; `string_expressions` is itself a JSON string of `[{key,value}]`: parse, edit, re-serialize compactly.

### Design rules for agent pipelines with several LLM steps
1. **Normalize user-facing labels once.** The UI dropdown sent "Weekly Operational Report" and "Technical Analysis" while prompts matched "Operational Report" / "Technical Analyst", so the new format silently fell through to the default layout (15 pages) and "Weekly" leaked into headings. Read the real payload/labels first, normalize at the config-extraction job (e.g. `contains(format, 'X') && 'X' || format`), and make prompts match the normalized value. Unknown values should not silently become a default.
2. **Audit what each worker is actually passed.** Two of three parallel synthesizers had prompts referring to `reportFormat` but their user prompts never included it (so their format-specific caps never fired). For every Base Agent, check that each input its system prompt mentions appears in its user prompt. The user's free-text guidance/intent is the commonest miss: it was passed to the planner only, while the content workers' prompts referred to "the intent input". Put it in the shared raw-content header so every worker sees it.
3. **JMESPath null-safety when a path omits keys.** `length(x)` on a missing key is a hard error (the run dies with "invalid type for value: None"), so a format that omits sections broke the existing *Extract Content* job. Use `length(x || \`[]\`)` and null-safe comparisons everywhere downstream of a step whose outputs are conditional; scan every job that reads those keys when you add a conditional path.
4. **Validate between LLM hops.** One identical run failed then succeeded (non-deterministic malformed/truncated model output is the likely cause). Add a deterministic JMESPath/Template check that required keys exist after each LLM job, and route failures to a degraded section or a retry instead of failing the whole run.
5. **Prompts must not hard-code time cadence** unless the data window dictates it.
6. **Pass the primary subject as content, not just ids** (LLM-5). If the pipeline selects objects (a TQL result, a group, indicators) and then fetches things around them, shape the selected objects too: for groups include the AI `insights.summary`/`bullets` of Reports and Events, for indicators the scores and owners; carry association stubs (`{id, name|summary, type}`) on each object gated by the user's "include associated data" toggles, and join stubs to full objects by id deterministically. Put the basis, criteria, time scope, returned-versus-limit and user guidance in a header, and give every worker a section explaining how to read each block per basis (what is primary, what is context, what to do when context is empty). Compute counts and breakdowns from the correct set for the basis.
7. **Adding a content domain to a multi-LLM report pipeline touches every closed vocabulary** (LLM-6). Checklist: data shaping job -> knowledge-block merge -> raw-content blob -> each worker's schema/rules -> content-flag/count extraction -> planner (valid keys, conditions, ordering, component mapping) -> section builder rule for the component -> template branch -> sources list. Gate an optional domain in the planner by explicit conditions (a basis, or the guidance asking for it) so existing report types do not change. After the build script runs, search the whole definition for the new key and confirm each place; then regression-run the existing formats.
8. **Temporary test knobs**: when isolating a defect by changing a cap or limit in a prompt (e.g. row cap 15 -> 3 -> 10), label it `TEMPORARY TEST CAP` in the prompt text, put the value to restore in the push note, change only that one thing per push, and restore it when the cause is found. Ask the user which value to leave live between experiments.

### Testing agent-trigger playbooks (UI-driven, not webhook)
- Agents launched from the Report AI page are exercised through the UI, not `test_webhook.sh`: use the `playbook-qa` skill, section 8 (report UI adapter), which also has the browser pitfalls (never click blind; read the report from the editor iframe; poll about once a minute; runs take 2-5 minutes).
- A failed run only shows "AI report generation failed." in the UI (and that banner can be wrong: check the execution status). To find the failing job, either read the execution's steps (`references/execution_logs.md`; slow, only if really needed), ask the user for the failing job from the Designer, or build observability in (e.g. a Fail branch that returns a small HTML report naming the failing step, so the message appears in the UI instead of a generic failure).
- Re-run a failure once before diagnosing; record both outcomes. Render checks that matter for report playbooks: page count, tables intact (the viewer flattens tables taller than ~950px), footer/page numbering, and wording hygiene.
- Validate any TQL with a direct v3 `GET ... ?tql=...&count=true` against the target instance first, so the expected input count is known before you spend minutes generating.

### Trigger payload drift: make the first extract job tolerant (any agent or webhook playbook)
The UI or caller that launches an agent owns the payload and can change it between releases (keys dropped, renamed, or replaced by a reference such as `styleReference` instead of a `style` object). The first JMESPath job usually reads many keys, and a missing key is null:
- `join()`, `length()`, `in()`, `sort()` on null raise "invalid type for value: None" and kill the run before any work; `to_string(null)` silently returns the text `"null"`.
- Write every read as `key || <default>`: `(x || \`[]\`)` for arrays, `x && to_string(x.y) || ''` for strings, `n || \`1\`` for numbers. Required keys should fail with a clear message rather than a null error.
- Normalize enumerated labels once here (lower-case, strip spaces, `contains`) so later jobs match only a canonical value; `"ExecutiveBrief"`, `"Executive Brief"` and `"Weekly Executive Brief"` must all land on the same layout.
- When someone reports a failure in this job, ask for the exact payload and run `playbook-explorer`'s `scripts/payload_contract_check.py <playbook.json> '<payload>'`: it lists the keys the job reads, which are missing, and which reads are unguarded. Fix, push, activate, and re-run with the same payload. Save the payload next to the playbook as the contract; re-check it whenever the UI changes.

### Moving a change to another instance (or to a copy someone else edited)
- Ids inside a definition (app catalog items, LLM config, trigger/job ids) are instance-specific. Do NOT push an export taken from instance A onto B's copy.
- Instead: fetch B's LIVE copy, apply a small patch script that locates its anchors by content (a job name, a unique string in the template; assert each anchor occurs exactly once), validate (balanced template tags, diff against live shows only the intended change), then push. Keep the patch script in the project so the same change can be replayed on the next instance. `diff_playbooks.py` also compares scope variables, so a template-only patch shows up.
- **When the user says they have moved to a new instance, verify lineage before assuming continuity**: fetch by groupXid, then check for markers from your last pushes (a job name you added, a unique string in a prompt, a version number) and re-check `logLevel`, which does not always carry over. Keep the new instance's backups under its own groupXid folder and work files separate from the old instance's.
- If `push_playbook.sh` output is truncated by the diff, read the new draft id from `<backup_root>/<groupXid>/CHANGELOG.md` (it records `old id -> new id`), then activate that id.

### Report/HTML templates and the report viewer (FTL)
The AI report viewer paginates by structure, not by CSS: each top-level `<section>` is a page; inside a flowing section, direct-child blocks are placed whole and CSS `break-*` rules are ignored; tables taller than ~950px are flattened (a fix is expected, re-check). So: (1) wrap each section's eyebrow + heading + content in one block to keep a title with its content; (2) to force a page break, close the current top-level section and open a new one in the template loop, and extend any `#id`-keyed CSS to the new id (`:is(#a,#a-2)`); (3) cap or split big atomic blocks (long lists, source lists) that leave white space; (4) verify by measuring per-page block heights in the editor iframe (see `playbook-qa`), not by eye. See FTL-5 in `playbook-explorer/references/best_practices.md`.

**Localising a rendering defect.** The wrappers the viewer adds (page containers, footers, class-less `<div>`s) are not in the template. When output looks wrong, first read the template job's own output in the execution log: if the markup there is valid (for example a proper `<table>`), the playbook is fine and the defect is in the viewer layer. Then bisect on one dimension (table rows 1, 3, 5, 10; section length; page position) to find the threshold and hand the engineer that table, not a guess. A tested data point: a table rendered at 1 row (5 columns) and 3 rows (4 columns), and flattened to plain text at 5 to 10 rows (4 columns, one-line rows, even when it fit on one page), so until the viewer supports multi-page tables keep tables short, or use a div-based component (a rated list survives page splits but looks busier for dense data such as hash lists). `playbook-explorer`'s hand-off brief template (`references/handoff_brief_template.md`) is the format for passing this to a viewer engineer.

### Report pipelines with an LLM stage: variant workflow, deterministic stages, template notes
- **Variant workflow that worked.** Export the live copy; build a new variant with an anchored `sub()` build script (asserts each anchor occurs exactly once; keep it as the single source of truth and rebuild from it each time); create it with `POST /api/v2/playbooks` (new groupXid, trigger renamed); verify by read-back (job count, every `#App` reference resolves, edited prompts present); activate; then iterate with `push_playbook.sh --brief` (dry run, then `--yes`) and activate the parsed draft id. The job summary printed by `--brief` omits scope variables (report templates live there): inspect them separately after a template edit.
- **Add a Base Agent job in series.** Copy an existing Base Agent job object (new id, new `languageModelConfiguration` id, own prompts, lower temperature and token cap) and replace the one edge `X -> consumer` with `X -> new -> consumer`; the consumer's prompt references `#App:<newId>:agent.out!String`; the server renumbers ids consistently.
- **Prompt-only fixes do not hold for LLM rule-following**: a rule obeyed in one render was broken in the next. Prefer a lower temperature on workers that must follow rules, deterministic JMESPath/FTL steps for anything countable or checkable (counts, slot arithmetic, dedup guards, dropping empty sections), few-shot examples in a small parser job, and exact counts passed into prompts (the model copies numbers, never counts).
- **Deterministic stages before and after the LLM (digest reports).** (1) A Template Builder "precompute" job derives grouping keys from item titles, flags promotional items and emits clusters as JSON plus a marked text block; (2) the prompt says one story per cluster; (3) a second Template Builder job builds fallback stories (headline, bullets, chips, source) from each item's own fields; (4) the assembler moves stories to the section that fits their badge, backfills to the requested total and lists unused clusters as "Also reviewed". In one test this held the requested story count (6 of 6) where prompt rules alone gave 4 of 6 in several versions (one confirming render so far). Mark machine-built stories visibly.
- **FreeMarker cannot run offline without Java**; do a tag-balance check (`<#if`/`</#if>`, list, macro, function) after every edit and treat the first live run as the test. Specific pitfalls are in the explorer skill's `ftl_debugging.md`.
- **Contrast guard in a template**: parse injected colour tokens (for example background and text) with `?matches`, compute the brightness difference (0.299R + 0.587G + 0.114B, threshold about 125) and override text, muted and border tokens when too close; extend to accent colours if needed.
- **Instance-level styling arrives in the payload** (`style.colors`): the playbook's fallback palette applies only when none arrive, so "the report looks different today" can be a branding setting, not a playbook change. Never edit instance settings such as branding without asking.
- **Format label normalisation**: UI labels change over time; normalise once in the config-extract job with `contains` variants and keep a similar older format out of the match list.
- **Process for test copies**: a push is followed by activation, and after programmatic activation the user must disable, refresh and re-enable in the Designer to see execution data (see `playbook-qa`, 8.11).

## Worked example 3: TC-to-TC feed distribution — native DataStore watermark + cross-instance file sync (instance C, Oct 2026)

A non-agentic, pure data-plumbing pair of playbooks: a producer webhook exports Reports (with native `insights`/attributes/tags/associations intact) from one TC instance, and a consumer webhook on another instance ingests them time-gated by a persisted watermark, submits everything in one unified Batch call, then separately syncs each Report's original attached HTML file over. Full app-level details (DataStore read/write shape, the file-sync chain, the Batch payload shape) are in `playbook-explorer/references/app_type_cheatsheet.md`; this section is the design narrative and the mistakes that led to the final shape.

- **Use `TCPB - DataStore v4` for a playbook's own cursor/watermark, not a placeholder Group.** An earlier design created a dummy Group purely to stash a timestamp in one of its attributes — DataStore is the native, intended mechanism and removes that whole workaround. See `app_type_cheatsheet.md`'s DataStore entry for the exact GET/extract/POST job shapes, including the `datastore.data.string`-is-undefined-when-absent crash and its fix.
- **Resist the temptation to branch on "first run vs. subsequent run."** `fail_on_not_found: true` plus an `If/Else`-style Pass/Fail split (agent prompt text and user's own request pointed this way initially) looks like the obvious design, but it requires the two branches to reconverge downstream — which hit the branch-convergence/fan-in limitation (see `gotchas.md`). The simpler, confirmed-working design never branches at all: leave `fail_on_not_found: false`, extract `_source.data || ''` from the DataStore response, and let an empty string naturally mean "pull everything" in whatever comparison consumes it (an empty string sorts before any real timestamp).
- **Carrying a file/binary attachment between two TC instances must avoid any `body`-type HTTP parameter.** The obvious design (fetch the file's bytes from a second producer-side webhook, forward them into another HTTP call's `body`) silently corrupts the bytes — see the `body`-field JSON-escaping gotcha. The confirmed working chain instead: `HTTP Client` (fetch, String) -> `Binary Operations` ("Convert from String", String -> Binary) -> `Get Groups` (`tc_action: "ID"`, resolve a `TCEntity` for the local group) -> `Update Groups` (`entities` + `file_content` + `file_name`). Validated byte-identical at real ~6MB file sizes (aside from the Binary Operations Unicode-punctuation-to-`?` defect, an accepted known limitation).
- **A per-report loop over a variable-length result set uses an `Iterator` fed by `map()`-built parallel arrays**, not three independent JMESPath projections — see JMES-1 in `playbook-explorer/references/best_practices.md` for why a bare `[*]` projection breaks index alignment the moment any item has an optional field unset (here: a report with no attached file).
- **Closing that Iterator's loop didn't need a `Merge` job** — confirmed later (reviewing a user-modified export of this same playbook deployed to a different customer instance) that the `EndLoop` edge can go directly from the loop's last body job back to the Iterator. The earlier build had used `Merge` as a loop-closing placeholder out of habit; it was dead weight.
- **Matching a Report across instances by name requires TQL-safe escaping of embedded quotes.** A real report titled `Example: Actor's "Named-Group" Hacking Collective` surfaced that TQL needs backslash escaping (`\'`, `\"`), not SQL-style doubling, which parses fine but silently matches nothing — see the TQL gotcha in `gotchas.md`. The escaping itself has to happen in a JMESPath step upstream of the TQL-building job; building the "backslash immediately followed by a quote" literal in JMESPath's own string-literal syntax is non-trivial (worth a look at `jmespath-assistant` if this comes up again — this specific escape-sequence trick isn't filed there yet).
- **Confirmed the whole design is genuinely cross-instance portable**, not an artifact of testing producer and consumer on the same instance: a user-deployed copy of the consumer playbook on a separate customer TC instance successfully called the producer webhook hosted on instance C over the open network and completed the full sync.
- **Still open, not solved:** `TCPB - ThreatConnect Batch Import v2` hard-crashes on a fully empty payload (see BATCH-1 in `best_practices.md`) — a time-gated sync that happens to have zero new items on a given run will hit this. No generic guard has been built yet; flag it if a user's design can produce an empty sync.

## Worked example 4: chat-based (Ask AI) agent that looks up intel for a named entity (actor hunt-pack generator, instance A, Oct 2026)

Pattern for any "parse the user's request -> fetch TIP data -> LLM writes the answer" chat agent. Build ONE script that emits two variants from the same job chain: a **webhook test harness** (HttpLink trigger + a JMESPath `query` extractor; iterate in seconds, no UI) and the real **Agent** trigger (`type: Agent`, `chatTriggerTypes: Global`, `outputVariables` `trg.agent.body` = the user's message; copy the trigger from an existing chat-agent export, set `conversationHintJson` examples, `httpResponseBody` = Merge output, drop `scheduleType`). Prove the chain on the webhook variant, then create the Agent variant with `POST /api/v2/playbooks`. The agent's playbook `description` is what Ask AI routes on: write it as "Use when... Not for...". Field-by-field reference for the Agent trigger: `playbook-explorer/references/app_type_cheatsheet.md` ("Agent trigger"); QA steps for Ask AI: `playbook-qa` section 2.1.

**Retrieval-eval echo harness (compare search configurations).** To compare Knowledge/search settings (e.g. `Keyword` vs `AiSearch`) without generating reports, build a webhook playbook with body `{"query","mode","start"}` and one search path per `mode`; a temperature-0 Base Agent only echoes the attached results (id, type, name, score, tags) as JSON, and the trigger returns it with `content-type: text/plain; charset=utf-8` (non-Latin titles break otherwise). Set the search item's `lastModifiedMin` from `start`, `limit` high enough to see the tail, and note that the endpoint UUID changes each version. A combined mode (two Knowledge items on one agent) works but does not de-duplicate. Scoring and judging procedure: `playbook-qa` section 17.
- **Entity extraction**: a small Base Agent returns `{"actor": ..., "names": [primary + aliases]}` (or `null`); a JMESPath job builds the TQL fragments (`join`/`map(&join('', [...]), names || \`[]\`)`) and a `NO_ACTOR` sentinel; If/Else branches to a friendly message. Test the fragments offline with `jmespath_local_test.py` first.
- **Build TQL with single quotes** in JMESPath-built fragments (`summary in ('a','b')`): TC accepts them and substituted values cannot break the JSON `params` string. Exact name match (`summary in (...)`) is case-insensitive; alias match needs whole-token patterns (`text = 'X' OR text like 'X, %' OR text like '%, X, %' OR text like '%, X'` inside `hasAttribute(typeName = 'Aliases' AND (...))`; the attribute value subject is `text`) because plain `like '%APT1%'` also matches APT10/APT15.
- **`strip_quotes` must be `true` on every JMESPath job that outputs plain strings you reuse** (ids lists, counts, names). With `false` the value keeps surrounding quotes (`"123,456"`), which silently breaks later TQL and `equals` checks (symptom: empty 200 body). `true` leaves JSON arrays/objects intact.
- **A JSON-only extractor on `tc_fast` wrapped output in ```json fences** and the Parse job died silently; `tc_balanced` plus the exact wording "first character must be {... Do NOT wrap it in markdown code fences (no ```json, no ```)" fixed it (4/4 runs).
- **Bisect silent failures with truncated builds**: a small script (`debug_truncate.py`) copies the built JSON, keeps jobs up to stage N, wires consecutive kept jobs, and sets the trigger's `httpResponseBody` to the raw outputs of that stage; push, activate, call, read. Located three bugs in four pushes. Rewire edges between consecutive kept jobs, or activation fails with `Invalid Variable Reference`/`Must have a source`.
- Give the LLM exact shown/total counts from JMESPath (`to_string(length(data || \`[]\`))`, `to_string(count || \`0\`)` with `count=true` on the fetch); it miscounts lists itself.
- Don't run two `test_webhook.sh` calls in the same second: the saved file name (timestamp + version) collides.

### Worked example 4, part 2: a second topic, a follow-up offer, and creating a TIP object from chat state (Oct 2026)
- **A second subject type is a branch, not a second playbook.** The extractor returns `topic` (`actor` | `technique` | `create_case` | `decline_case` | null) plus the ids/names; a Parse job turns it into one `topic.kind` value (`ACTOR`, `TECHNIQUE`, `CASE`, `DECLINE`, `NONE`) and a chain of If/Else jobs routes on it (each Pass/Fail pair). Every terminal branch (pack agents and message jobs) feeds the one Merge that the trigger returns; give every message job the same output name (`error.message`) and list them all in the Merge expression. Add the producer->Merge edge for each. Technique intel in a TIP: Attack Pattern groups named `T1574.002 - ...` (match `summary like 'T1574.002 %' OR summary like 'T1574.002.%'`), the reports linked to them (`hasGroup(id in (...))`, newest first with `fields=insights`), actors/tools by `hasTag(techniqueId like 'T1574%')`, IOCs via the nested `hasGroup` form. A parent ID covers the family; when the user names a sub-technique in words, narrow to it.
- **Follow-ups that need the previous answer: Cache Store/Lookup keyed by conversation id.** Store the pack on a dead-end branch off the pack agent (`cache_name` `<Prefix>-#Trigger:<id>:trg.agent.chatconversationid!String`, `cache_key`, `expire_seconds` 86400); on the follow-up turn Cache Lookup with `fail_on_miss: true` and a **Fail** edge to a "no stored pack" message (a miss then answers cleanly). Referencing `trg.agent.chatconversationid` is what keeps it declared on the trigger (it is dropped from `outputVariables` otherwise). The extractor sees earlier turns (`messageContextWindow` 6), so a bare "Yes" after the assistant's offer is classified `create_case`; tell it a bare "yes" without a preceding offer is not.
- **Offer line**: instruct the pack agent to end with `---` and the exact offer sentence; strip it from what you store with String Operations `Replace` (`replace_old` = the sentence, `replace_new` empty, `replace_count` defaults to 1).
- **Creating a case**: `POST /v3/cases` with `{name, severity (Low|Medium|High|Critical), status, description, notes: {data: [{text}]}}` through `TCPB - ThreatConnect API v3`. The note limit was not hit at 30,000 characters.
- **Never put raw LLM text straight into a JSON `body`.** A JMESPath job's string output (with `strip_quotes` true) is already JSON-escaped, so a sandbox that fed the text through JMESPath passed while the real chain (Cache Lookup -> Replace -> body) failed with "JSON ... could not be mapped". Build the body with **JSON Operations `Build JSON`** (`json_data_build` = the body template, `indent` 4, output `json.formatted`) and pass `#App:<id>:json.formatted!String` as the whole `body`. In that template **every reference must be the entire string value** (`"name":"#App:..!String"`); a reference inside other text (`"Threat Hunt: #App:..!String"`) makes the job fail silently, so build such strings upstream (a JMESPath `join('', [...])`). The raw note text itself as a whole-value reference is escaped correctly.
- **Template jobs copied from another playbook can be disabled**: the JSON Operations template had `"active": false`, so the job never ran and its output stayed an unresolved placeholder. Print `active` on every template you copy and set it `true`.
- **App catalog ids and versions differ per instance.** A push can fail with `apps are missing: String Operations` when the template's app version (2.0.7) is not installed on the target (2.0.0). Keep one template per instance for the apps that fail (take the job from a playbook already on that instance) and select it with a build argument; other apps (Cache, JSON Operations) were present.
- **Long pushes**: a large POST to one instance hung for minutes once; run `push_playbook.sh` with output to a file in the background, kill and retry if it stalls (the instance itself stayed healthy).
- **Test matrix for an offer flow** (webhook twin first, UI after): pack -> bare "Yes" (case created, note holds the full pack, offer sentence stripped, verify via `GET /v3/cases/<id>?fields=notes`), "no thanks" (decline message, no case), case request with nothing stored (miss message), unknown subject, no subject. Leave sandbox cases named "ZZ ... - delete me" and tell the user.

## Testing Group/Report-event-triggered playbooks (no webhook, no UI) — worked example: instance C `<id-C>` "Report Post Processing", Oct 2026

Not every playbook is webhook- or chat-triggered. This one fires on a native TC object lifecycle event: trigger `type: Report`, `eventType: AddTag`, with a `playbookTriggerFilterList` requiring `Tag Equals PROCESS`, scoped by `organizationNames: ["Example Owner"]`. There is no endpoint to call at all — `playbook_ctl.sh status` correctly reports `no-endpoint` for this trigger type.

- **Read the trigger config to learn what actually fires it, before trying to test anything.** `playbookTriggerList[0]` names the object type, the event, any field-level filter, and the owner scope — treat this the same way you'd resolve a webhook's endpoint: it's the precondition for a live test, and guessing at it wastes a round trip.
- **To fire it, perform that exact mutation on a real object via direct v3 API**, in the scoped owner: here, adding the `PROCESS` tag to a Report group (`POST`-equivalent tag-add call against `/api/v3/groups/{id}/tags/...` or the UI). Since it's an `AddTag` trigger (fires on the tag transitioning from absent to present, not on its mere presence), **re-testing against a group that already carries the tag requires removing it first, then re-adding it** — simply confirming the tag is still there does nothing. Easier in practice: keep 2-3 disposable test objects in the scoped owner and rotate between them so you never need a remove+re-add cycle mid-session.
- **There is no response payload to inspect at all** (unlike a webhook) — confirm the result by reading the mutated object back afterward (e.g. `GET /api/v3/groups/{id}?fields=attributes` to check a Description attribute the playbook is supposed to have written) rather than looking for any kind of return value from the trigger action itself.
- **v2 Group/Owner read endpoints 400'd on this instance even with correct auth** (`/api/v2/groups/reports/{id}`, `/api/v2/owners`) while v2 Playbooks worked fine — switched to v3 (`/api/v3/groups/{id}`, `/api/v3/groups/{id}/tags`) and everything worked immediately. See `references/api_notes.md` for the full note; don't assume v2 parity across resource types on an instance just because the Playbooks API works.
- **Fetching the actual report HTML content for feasibility-testing a new HTML-parsing job** (checking real input shape/size before writing a system prompt against assumptions): `GET /api/v3/groups/{id}/download` returns the raw file. This mattered concretely here — the report's `fileSize` was 6.4MB, which looked alarming for feeding into a Base Agent, but after the playbook's own existing `<head>`-strip and `<img>`-strip regex steps the actual text reaching the agent was ~12KB (~3K tokens): most of the raw size was inline base64 CSS/fonts in `<head>` and one or more embedded images, not report prose. Measure the real post-pipeline size on an actual sample before assuming a Base Agent step is infeasible (or safely feasible) on size grounds alone.
- **Adding a brand-new Base Agent job into a playbook that had zero agent jobs before hit the connection-edge gotcha** described under "Adding jobs and branches" above — the fix was adding the missing producer -> consumer connection edge, not anything about the output variable name or declaration.
- **Attribute size limits are real and worth checking before committing to an inline-content design.** This playbook's new job converts report HTML to Markdown for a group's `Description` attribute; `GET /api/v3/attributeTypes` showed `Description` has `maxSize: 102400`. The report's actual embedded images alone (once de-duplicated — see the next point) totaled ~433KB of base64, over 4x the limit, found by direct measurement (`grep`-style regex extraction of `<img src="data:...">` tags from the real downloaded HTML) before any job was built around inlining them. Check `maxSize` against realistic sample sizes early, not after an Attributes app job starts failing.
- **Report HTML exports can duplicate their own content via print-pagination markup.** This report's body appeared once in a primary flowing container and then AGAIN, split across several `reportpage-text-block` divs separated by `reportpage-divider` elements (a print/page-break layout artifact) — a naive HTML-to-Markdown conversion would double every paragraph. Caught by eyeballing the actual downloaded+cleaned HTML before writing the conversion prompt (not by a failed test run), and handled by explicitly instructing the conversion agent to recognize and de-duplicate this specific structural pattern rather than assuming the DOM is a single flat document. See CONV-1 in `playbook-explorer/references/best_practices.md`.
- **Design recommendation, not yet empirically run end-to-end:** to preserve embedded images in a generated Markdown output without routing their binary through the LLM's context (expensive, and a bad fit for a model to reproduce byte-for-byte anyway), extract each image's data URI deterministically into an array and replace it in-place with a short placeholder token (e.g. `[[IMG_0]]`) before the conversion agent ever sees the HTML; have the agent carry the token through verbatim; splice the real data back in with a final deterministic Find/Replace or small `Iterator` keyed by index. See CONV-2 in `playbook-explorer/references/best_practices.md`.

## Worked example 5: adding a "precision backstop" LLM agent alongside a primary extractor, and a 3-round adversarial QA/fix campaign (same instance C playbook, Oct 2026)

Continuation of the worked example above. Two more agent jobs were added to the same playbook: one
that independently extracts named threat-actor/malware entities (to catch what a MITRE-bound
primary extractor misses), and one that does the same for IOCs (to catch and correct a context-blind
extractor's false positives). The entity-extraction lessons themselves — relevance filtering, guilt-
by-association, persona-vs-collective, victim-domain exclusion, pattern-list recognition — are
written up generically in `playbook-explorer/references/best_practices.md`'s new EXT-1
through EXT-9 (read those for the prompt-design content); this section is about the *build and QA
process* that surfaced them.

- **The "Knowledge" context mechanism (`#Knowledge:<jobId>:...`)** lets a Base Agent see a live TQL
  query result from the instance's own data (e.g. "these are the entities already tracked"),
  configured via `userContext` in Designer — see `app_type_cheatsheet.md`'s Base Agent entry for the
  exact shape. Confirmed real value: letting a second extraction pass recognize an alias of
  something that already exists, instead of creating a duplicate under a new name. Confirmed real
  pitfall: wording this carelessly can make the model treat "already exists" as a reason to omit the
  entity entirely from its output, which silently breaks re-association with every future report
  about an actor the instance already knows — the fix is one explicit sentence that the list changes
  naming only, never inclusion (EXT-5).
- **Validate-then-deploy, every single fix, no exceptions — and a semantic diff per push.** Every
  prompt change in this campaign went through: re-fetch latest -> build the edit with an anchored,
  assertion-guarded script -> `diff_playbooks.py` to confirm only the intended param changed -> push
  -> activate -> re-fetch and verify the fix text survived activation (confirmed more than once that
  it doesn't automatically — see the connection-edge gotcha under "Adding jobs and branches") ->
  THEN isolate-test in a sandbox (ideally with real upstream context, see the sandbox-fidelity note
  above) before trusting the fix. Skipping the isolate-test step and deploying straight from
  reasoning about the prompt text alone would have shipped at least one regression (a tightened
  "exhaustiveness" instruction that, in testing, caused a previously-correct IP-type filter to start
  over-including CloudFlare-proxy ranges) before it ever reached production.
- **A full QA campaign needs full re-validation after every fix batch, not just a recheck of the
  cases that failed.** The confirmed-working pattern (paired with `playbook-qa`'s own new
  section on this): after each batch of fixes, delete everything the playbook creates and re-fire
  every test case from a clean slate, then re-run the FULL validation suite — including the cases
  that already passed — because a fix aimed at one report's defect can have an unintended side
  effect on another (confirmed: fixing a different report's issue this way incidentally recovered a
  third report's missing value as a side effect at least once, and separately, two cases flickered
  between pass and fail across identical reprocessing runs with no prompt change in between, which
  is the signature of genuine model non-determinism on a borderline-confidence candidate rather than
  a deterministic logic gap — worth distinguishing the two, since the fix for one is prompt wording
  and the fix for the other is more likely a lower `temperature` or a deterministic completeness
  check as a safety net).
- **Before trusting a "missing value" as a pipeline bug, verify the ground truth itself.** A real
  case: a report's own manually-curated reference IOC list (added by a human analyst) turned out to
  share zero actual overlap with that same report's attached document — confirmed by grepping every
  one of the reference values against the raw file and finding none of them present. This was a
  pre-existing data-association mistake in the source system, confirmed by the person who'd created
  the association, and not a defect in the playbook at all. Don't assume a "ground truth" comparison
  set is itself correct — spot-check it against the actual source document before spending more time
  chasing a gap that may not exist.
- **TQL `in (...)`/`ownerName` scoping mistakes look exactly like "the reset didn't work."** See
  `references/api_notes.md`'s new note on this — confirmed during this campaign's repeated
  clean-slate checks between QA rounds.

## Worked example 6: diagnosing and fixing a silent total-result-loss bug, and tightening two relevance-exclusion rules via worked examples (same instance C playbook, continued, Oct 2026)

A production incident surfaced while scaling the same playbook from a 15-report test pool to a
32-report historical backfill: several reports came back with **zero** actors/malware extracted
despite clearly containing many named personas with real, substantively-described activity. This
is a different, more severe class of bug than anything in worked example 5 above — not an
imperfect-but-visible extraction, but silent total data loss that looked identical to "nothing in
this report qualified."

- **Diagnosis path that worked:** (1) read the suspect job's full config, not just its prompt — the
  `languageModelConfiguration.maxOutputTokens` was a reasonable first suspect but turned out not to
  be the cause; (2) reproduce in an isolated sandbox fed the REAL cleaned report text (see the
  sandbox-fidelity note above) with the SAME Knowledge/`userContext` wiring as production, by
  pointing the system prompt's `#Knowledge:<jobId>:...` references at the sandbox job's own id — a
  single sandbox call looked fine; (3) **test under concurrent load specifically** (8 simultaneous
  webhook calls via backgrounded `curl` + `wait`) rather than only serial calls one at a time — this
  is what reliably reproduced the failure (8/8 failed under concurrent load vs. clean serial runs),
  and it mirrors how the real pipeline actually invokes this job (many reports tag-cycled in a tight
  batch, each firing the same agent near-simultaneously); (4) directly verify the downstream
  JMESPath parse step's real tolerance by building a tiny sandbox job that feeds it a literal,
  captured messy real response (prose + JSON) instead of assuming how lenient it is — confirmed
  experimentally that it has zero tolerance for leading text, which was the actual mechanism (see
  JSON-8 in `playbook-explorer/references/best_practices.md` for the full write-up and the
  confirmed fix: few-shot examples of the literal terminal output in place of an open-ended
  self-check, not a token-budget change).
- **Validate a fix for this class of bug under the same concurrent load that reproduced it**, not
  just serial sandbox calls — confirmed 24/24 clean responses post-fix under the identical 8x
  concurrent load that was 0/8 beforehand, on the two worst-affected reports, before deploying to
  production.
- **A full-fleet regression check after a fix doesn't need full adversarial re-derivation on every
  item — a cheap, scripted names/counts snapshot before and after is enough to catch a regression,
  reserving subagent-based re-derivation for the specific items the fix targets.** Confirmed useful
  at 32-report scale: a before/after diff of each report's associated-entity names and counts (pure
  API calls, no LLM) caught zero regressions across the full fleet, while the 3 originally-broken
  reports were separately confirmed recovered with real entity names matching the independently
  pre-derived expected lists. This is a meaningfully cheaper validation strategy than re-running a
  full QA campaign's worth of subagents against every report on every change, and is the pattern to
  reach for whenever a fix needs "did this break anything else," as distinct from "does this specific
  fix work," which still needs targeted judgment-based review.
- **A probabilistic relevance-judgment lapse (not a mechanical bug) may not reproduce in isolated
  sandbox testing at all, even with faithful inputs and several trials.** Separately from the
  total-failure bug above, two existing exclusion rules (an IOC agent's citation-link rule and its
  victim-domain rule) were confirmed to be producing real false positives in production, but feeding
  the *unfixed* prompt the exact real report text plus the exact known-bad candidate values
  correctly excluded them in 7/7 isolated sandbox trials. The fix (the same few-shot-worked-example
  pattern as JSON-8, applied to the relevance rules themselves rather than output formatting) was
  still deployed on the strength of the diagnosis and a real-production re-run against the specific
  known-bad case — but be upfront when reporting this kind of fix that sandbox testing could not
  demonstrate a clean "before fails reliably, after passes reliably" cycle, and that real-production
  re-validation of the exact previously-failing object is the only solid confirmation available.
- **Reprocessing a large batch through a native object-event trigger (not a webhook) took much
  longer, and behaved much less predictably from API-based freshness checks, than expected** — see
  `app_type_cheatsheet.md`'s new "Native object-event triggers... batch-reprocessing reliability"
  entry. Cross-check the real target data or the Designer UI before concluding a bulk reprocessing
  job has stalled.


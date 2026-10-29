# Confirmed gotchas (learned the hard way, across real sessions)

## API version split: v3 for lookup, v2 for full definition
- `GET /api/v3/playbooks/{id}` → `{"errCode":"0x1005","message":"This operation is not supported"}`. v3 supports listing/filtering (`tql=groupXid EQ "..."`, `tql=name CONTAINS "..."`) but **not** fetching one playbook's full definition — no `/download`, `/export`, `/config`, `/definition`, or `/nodes` sub-resource either.
- `GET /api/v2/playbooks/{numeric_id}` returns the **full** definition (jobList, connections, triggers, scope variables). Always resolve an id via v3 first (if starting from a groupXid or name), then download via v2.

## Auth header
`Authorization: TC <TC_KEY>` — the `TC_KEY` value itself is typically a pre-built credential string like `APIV2:<accountId>:<accessId>:<timestamp>:<signature>`. (`TC-Token` and `Bearer` prefixes have also been observed to work against some instances, but `TC` is the canonical ThreatConnect scheme — use it.)

## Branching and loops ARE supported — don't assume a static DAG
An earlier, simpler playbook in this project used only static `Pass`-type connections with no branching, which was initially (and incorrectly) read as "this platform only supports static DAGs." A later, more developed playbook in the same project uses `If/Else` blocks and the user directly confirmed **Iterator** (loop over array(s), sequential execution, works with a **Cache Store** app for cross-iteration state) as a native construct. Don't infer a platform limitation from one playbook's structure — check for `If / Else`, `Iterator`, and `Cache Store` app types before concluding a pattern isn't supported.

## "Copy of X" jobs are often branch-exclusive, not redundant
When two near-identical jobs exist (same app, same params), check `playbookConnectionList` for which `If/Else` branch each sits under before assuming one is dead/duplicate work — they're commonly one job per branch, only one of which executes per run.

## MCP tool instance mismatch
If this session also has `mcp__threatconnect__*` MCP tools available, they may be connected to a **different** TC instance than the one holding the playbook you actually want (confirmed: an MCP connector pointed at instance D while the target playbook lived on instance B). Don't assume the MCP tools and a direct API call via this skill are hitting the same instance — check the base URL being used for each.

## `fields=common` is easy to under-request
The platform's unified/normalized object data (`commonGroup`: CVSS for Vulnerabilities, `priority`/`mitreId` for Threat Actor Profiles) only appears when a fetch explicitly requests `fields=common`. It's easy for a playbook to request it on one fetch (e.g. a top-level query) but miss it on a related one (e.g. a downstream category-specific fetch) — when reviewing a playbook, check this per-job rather than assuming consistency across similar-looking fetches.

## Unified-object queries (`hasCommonVulnerability`/`hasThreatActorProfile`) don't cover everything
- Alias resolution only works via the MITRE primary name (e.g. "APT28" works, "FANCY BEAR" does not).
- Non-MITRE-tracked actors (common for ransomware crews) have **no** unified Threat Actor Profile at all, so `hasThreatActorProfile()` will never match them regardless of name. Don't use unified-object presence as an inclusion/exclusion filter for actor-type content — it would systematically exclude a real and often high-priority class of threat. Use it as a secondary confidence signal or a richer-data source, with a plain `typeName`-based query as the fallback path for everything without a profile.

## A project can have several similarly-named playbooks across several instances — verify, don't assume
Confirmed the hard way: a project had a playbook named "Generative Report Agent - Scheduled Test" that existed as **two separate xids on two separate instances** (one stale/abandoned, one live and actively edited), plus an unrelated earlier playbook with a similar name on yet another instance. Re-fetching "the same" playbook repeatedly produced no changes for several turns before realizing the wrong xid was being pulled the whole time — the live one was on a completely different host. When a user refers to "POC" or "the agent" by a loose name rather than an exact id/xid, and especially if a re-fetch ever shows *no* expected changes after work was supposedly done on it, **stop and confirm the exact xid and instance** rather than assuming continuity with whatever was fetched earlier in the session.
- Watch for **multiple instance-specific `.env`-style credential files** in a project (e.g. `.env_instanceA`, `.env_instanceB`, `.env_instanceC`, `.env_instanceD`, alongside a bare `.env`) — this is a real, confirmed convention, not a hypothetical. Check for these before assuming one `.env` covers whatever instance is being discussed.
- A playbook's **internal numeric id can change across saves even when its groupXid stays stable** (confirmed: same groupXid, numeric id changed between two pulls a couple of weeks apart). Never cache/reuse a numeric id across sessions — always re-resolve via groupXid (or re-run the fetch script) before trusting an id.
- **Individual job ids inside a playbook also change across versions/edits** (confirmed: a job's id changed between two versions of the same playbook, a couple of version-numbers apart). Don't hardcode a specific job id remembered from earlier in a long session without re-confirming it against a fresh pull — look the job up by name again instead.

## When comparing/migrating between two playbooks, filter out job-id-reference noise first
Diffing two playbooks' prompts/templates almost always surfaces a flood of differences that are just internal `#App:<jobId>:...` references pointing at different (but structurally equivalent) job ids between the two playbooks — not real content differences. Diff the actual prompt/template text, but expect — and discount — lines that differ only in the numeric job id inside a `#App:...`/`#Global:...` reference. `scripts/diff_playbooks.py` (bundled with this skill) does this filtering automatically; prefer it over a raw `difflib` diff, and double-check the direction of any genuine diff it surfaces (which playbook has the extra/different text) before reporting it — it's easy to get backwards when skimming a unified diff quickly.

## LLM-based matching/joins between two lists are unreliable — do it deterministically instead
A playbook attempt to have a Base Agent job match items from one list against another (e.g. matching a short code against a lookup table of `{id, name}` pairs, to attach an id for link-building) produced very low match rates even with an explicit, clear instruction — most items came back unmatched despite real matches existing in the data. This is a deterministic join problem, and handing it to an LLM buried inside an already-busy prompt is a poor fit regardless of instruction quality. If a future playbook needs this kind of lookup, do the join with JMESPath (or another deterministic step) *before* the data reaches any Base Agent job, so the LLM only ever has to pass an already-resolved field through, not compute it.

## Branch convergence (fan-in) is not safe to assume — confirmed broken on at least one instance
Two mutually-exclusive branches (an `If/Else` Pass/Fail pair, or similar) reconverging on one shared downstream job is a different thing from a job merely having two possible upstream paths wired to it on paper — confirmed on instance C that the shared job simply never fires, in three different shapes: a plain job with two incoming Pass edges, a dedicated `Merge` app used the same way, and a full production playbook using the same pattern. Each branch worked perfectly in isolation; only the reconvergence was broken. The same general shape is documented working on a different instance (instance A) elsewhere in this project, so don't treat this as a universal platform rule in either direction — smoke-test fan-in in isolation on whatever instance you're building for before relying on it. Fan-OUT (one job's Pass driving multiple independent downstream branches that never rejoin) is unaffected and confirmed reliable everywhere tested; prefer redesigning around fan-out (e.g. a "side" branch that does extra work in parallel, not gating the main response on it) over fighting a broken rejoin. See `app_type_cheatsheet.md`'s `Merge`/`Iterator`/`DataStore` entries for the concrete patterns this affects.

## A `body`-type HTTP parameter corrupts any raw/binary payload referenced into it
Confirmed via byte-level diff (`cmp -l`) on real multi-MB content: referencing another job's String output into ANY job's `body`-type parameter (seen on `TCPB - ThreatConnect API v3`, likely true of similar HTTP-style apps) silently applies JSON-string escaping to the actual bytes sent over the wire — wraps the value in quotes, escapes embedded `"` as `\"` (confirmed exact: +1271 bytes on a real payload, all from this escaping). The SAME value referenced directly into a trigger's `httpResponseBody` was confirmed clean. This is NOT fixable by re-escaping/unescaping tricks: a JSON re-parse fails on real non-JSON-safe bytes at that scale, and a String Operations "Replace" round-trip just re-corrupts on its own output's next reference hop (the corruption applies per-reference-into-a-body-field, not per-source-app). The actual fix is to never route file/binary content through a `body` field at all — see `app_type_cheatsheet.md`'s `Binary Operations`/`Get Groups`/`Update Groups` entries for the confirmed working chain (relay via a `Binary`-typed param instead).

## `outputVariables` can be silently stripped to `[]` on newer "business" apps
Trying to declare a custom `outputVariables` entry via a raw API push (not through the Designer UI) on apps like `TCPB - Binary Operations v2`, `TCPB - Threatconnect Update Groups v1`, or `TCPB - Threatconnect Get Groups v2` can get silently reverted to `[]` by the server. This isn't about getting the output *name* right — it only sticks once the REST of the job (especially `tc_action` and its companion params) exactly matches a configuration the Designer UI could actually produce. If a declared output isn't sticking after a push, stop guessing param combinations and instead copy a Designer-saved, already-working example of that exact `tc_action` (ask the user to configure one directly in the Designer if none exists yet) rather than hand-assembling the params.

## A copied job template's stale `layoutRequiredInputParams` causes false "required field missing" errors
Copying a job template that was configured for one `tc_action` (e.g. a String Operations job set up for `UUID5`) and then changing it to a different action (e.g. `Replace`) without also updating the job's STATIC `layoutRequiredInputParams` metadata can produce a spurious `Required field(s) missing: <param from the OLD action>` validation error that has nothing to do with the actual action you're configuring. Fix by either overriding `layoutRequiredInputParams` to match the true action's real requirements, or — more reliable — copy a template the user (or an earlier working job) has ALREADY configured for that exact `tc_action`, since its metadata will already be correct.

## JMESPath: a bare projection silently drops elements with a null/missing field
When building several same-length arrays meant to be fed into an Iterator's `array_inputs` in lockstep (e.g. one array of ids, one of names, one of filenames, all derived from the same source array), using a plain projection like `reports[*].fileName` silently DROPS any element where that field is null/missing — confirmed: a 2-element source array with one missing `fileName` produced only a 1-element result, breaking index alignment between the "parallel" arrays. `map(&fileName || '', reports)` preserves every element regardless of missing fields, applying the expression unconditionally per element — use `map()`, not a bare projection, for any array meant to stay aligned with a sibling array.

## JMESPath: a parenthesized expression right after a projection dot is invalid syntax, and fails silently
`reports[*].(fileName || '')` is NOT valid JMESPath. With `fail_on_jmes_expression: true` (the usual default), this silently breaks the ENTIRE JMESPath job — not just that one output — manifesting as an empty webhook body with no informative error anywhere in the response. Use `map(&fileName || '', reports)` instead of trying to inline a fallback directly after a projection dot. If a webhook response goes unexpectedly empty, suspect this pattern (or any other subtly-invalid JMESPath) in a `string_expressions`/`string_array_expressions` entry before looking elsewhere.

## TQL string literals: embedded quotes need backslash escaping, not doubling
A double-quoted TQL string value containing an embedded apostrophe or double-quote must use backslash escaping (`\'`, `\"`) — NOT SQL-style doubling (`''`, `""`). Doubling parses without a syntax error but silently matches nothing, which is a much worse failure mode than a clear parse error (confirmed via extensive direct API testing against a real report named `Example: Actor's "Named-Group" Hacking Collective`). When building a TQL value from a field that might itself contain quotes (e.g. matching a Report by its `summary`/name), escape both characters in the upstream JMESPath/transform step before they reach the TQL string, and test specifically with a quote-containing value — it's the kind of input that looks like it "shouldn't happen" until it does.

## TQL: single quotes, case-insensitive exact names, and whole-token alias matching
Confirmed on instance A/B (Oct 2026), looking up threat actor groups.
- TQL accepts single-quoted strings (`summary in ('apt28','fancy bear')`). Build JMESPath-made fragments with single quotes: a substituted value then cannot break the JSON `params` string.
- `summary in (...)` exact match is case-insensitive, so `'apt28'` finds `APT28`.
- Aliases live in `Aliases` attributes, one value per attribute or one comma-separated list. Search with `hasAttribute(typeName = 'Aliases' AND (text = 'X' OR text like 'X, %' OR text like '%, X, %' OR text like '%, X'))`: the value subject is `text` (`value`, `attributeValue`, `summary` are rejected, `displayed` rejects `like`). A plain `text like '%APT1%'` also returns APT10/APT15 groups; the whole-token form returned only APT1.
- `hasGroup(id in (a,b) OR hasGroup(id in (a,b)))` on `/v3/indicators` and `/v3/tags` is one group hop (intel on the actor's linked reports). The same nested form on `/v3/groups` is two hops and pulled in another actor's malware and unrelated CVEs: use the direct `hasGroup(id in (...))` for associated Malware/Tool/Campaign/Vulnerability.
- A JSON-parse step that gets fenced model output fails silently: see JSON-7.

## `strip_quotes: false` leaves quotes around string outputs
A JMESPath job with `strip_quotes` `false` stored `group.ids` as `"1,2"` (quotes included), and a `"0"` sentinel failed `equals 0`; the next fetch's TQL broke and the webhook returned an empty body. Set `true` for jobs that emit plain strings (JSON arrays stay intact). See JMES-4.

## A template job copied from another playbook may be disabled (`active: false`)
A JSON Operations job copied from an export carried `"active": false`: it was skipped silently and its outputs stayed unresolved placeholders in the response. When you copy a job as a template, check its `active` flag and set it `true`.

## JSON Operations `Build JSON`: references must be whole string values, and it escapes raw text
`json_data_build` is a JSON template. A reference that is the entire value of a string (`"text":"#App:<id>:x!String"`) is resolved and escaped correctly, including raw multi-line LLM text with quotes and backslashes; a reference embedded in other text (`"name":"Prefix #App:..."`) makes the job fail silently. Build such strings upstream. Pass its `json.formatted` output as the whole `body` of an API call. Do NOT reference raw text straight into a JSON `body`: JMESPath outputs are JSON-escaped already (so a JMESPath-fed test can pass), raw job outputs are not.

## App catalog id/version differs per instance: a push can say "apps are missing"
A definition copied from another instance can name an app version the target lacks (String Operations 2.0.7 vs 2.0.0): `Unable to install this playbook. The following apps are missing: ...`. Take that job from a playbook already on the target instance and keep it as an instance-specific template.

## Nullable fields break assumptions the rest of the pipeline has never had to face
If every existing prompt/schema in a playbook follows a "omit the key if there's no value" convention (common in this kind of pipeline — check for explicit "omit if empty/null" language across prompts), introducing a *new* field that's allowed to be JSON `null` can break generic downstream JSON-processing code (e.g. a hand-written recursive JSON serializer in a Template Builder) that has simply never been exercised against a real null leaf before, even though its own code looks like it should handle one. See `references/ftl_debugging.md` for the exact FreeMarker failure modes this produces and how to fix them. Before adding a nullable field to a schema, either match the existing convention (omit the key instead) or proactively harden whatever deterministic code consumes that schema.

## `diff_playbooks.py` compares scope variables too (templates live there)
An FTL/HTML report template or a long shared prompt is often stored as a playbook-level scope variable (`playbookScopeVariables`), not in any job's params. Older versions of the diff only walked `jobList`, so a template-only change showed "no differences". The script now also compares scope variables by name; when comparing by hand, check them separately.

## Instance-specific ids make cross-instance pushes unsafe
App-catalog item ids, LLM configuration ids and similar references differ between instances, so pushing an export taken from instance A onto instance B's copy can point jobs at ids that do not exist there. To move a change, fetch B's LIVE copy, apply a scripted patch that finds its anchors by content (a job name, a unique string), diff, then push. Do not rebuild from A's export.

## A missing payload key is null, and null has two failure modes
`join()`, `length()`, `in()` on null raise a hard error and stop the run. `to_string(null)` does not fail: it returns the text "null" and carries on. Check both when a trigger payload changes. See PAY-1 and PAY-2 in `best_practices.md` and `scripts/payload_contract_check.py`.

## UI labels are not the playbook's labels
The text a dropdown sends can differ from what prompts match ("Technical Analysis" vs "Technical Analyst", "Weekly Operational Report" vs "Operational Report", "ExecutiveBrief" vs "Executive Brief"). The mismatch produces no error, only the default behaviour. Read the real payload before writing format conditions.

## TC JMESPath library: several functions raise on null, and the failure depends on the record
`include_keys(x, ...)` needs an object, and `max_by`/`min_by` need every key expression to return a number or string: a null raises "invalid type for value: None" instead of being skipped. Because optional fields differ per record type (geo data exists on IP/host indicators, not on File indicators), a job can pass on one sample and fail on the next. Guard with `not_null(x, \`{}\`)` / `not_null(f, \`0\`)` and test against a sample with every record shape. See JMES-2 and `scripts/jmespath_local_test.py`.

## `regex('^.{0,600}', text)` stops at the first newline
`.` does not match a newline, so a length cap written that way silently truncates multi-paragraph text at its first line break (a description cut to "Written by"). Start the pattern with `(?s)`: `regex('(?s)^.{0,600}', text)`. Used successfully in production shapers.

## Group and indicator objects have different shapes
Indicators have no `insights` (`fields=insights` is rejected for them), no `commonGroup`, and carry scores directly (`threatAssessScore`, `calScore`, `rating`, `confidence`, `observations`, `falsePositives`) plus `sources`-style per-owner copies when the same value exists in several owners. Groups carry `insights` (`summary`, `bullets`, `markdown`; populated for Report/Event groups, empty for Adversary/Malware/Incident), and `commonGroup` (for example CVSS for Vulnerabilities and `commonGroup.linkedGroups.data`, the other owners' copies of the same entity). `associatedGroups`/`associatedIndicators` exist only if requested in `fields`. Check one real response per object type before writing a shaper.


## An LLM job feeding `?eval_json` can fail by narrating
When a Base Agent that must emit JSON feeds a template's `?eval_json`, it sometimes writes reasoning before the JSON (the error quotes the first words, for example `Invalid JSON keyword: "Junk"`), or it narrates until its output-token cap and never reaches the JSON (the error quotes the first word of the narration). Defences: (a) extract the object defensively in the Template Builder (return the trimmed text if it starts with `{`, else the first `{...}` block via `?matches('(?s)...')`); (b) tell the agent to work silently and output only the JSON, in both the system and the user prompt; (c) set `maxOutputTokens` generously for synthesis workers. Read the Designer log for the first failed template job: the error text shows the start of its bad input.

## Asset image tokens only survive inside a `<section>`, not a `<header>`
Confirmed in the Report editor: the `<header>` block is discarded and `<section>` blocks are kept. A platform image token (`<<assetImageId=NN>>`) placed only in the header never becomes an image, so a format with no cover section shows no logo. Put the token inside the first section and it becomes a real `<img>` at its natural size (588x640 here), so cap it in CSS with `max-height` and `!important`.

## "Completed" is not "good report", and a stricter empty-case rule can break the non-empty case
Confirmed: adding "return exactly `[]` when a slice is empty" to a section-builder prompt made the worker return `[]` for every slice, so the run finished Completed with no stories. Reverting the wording fixed it; the lasting fix was a deterministic parser in the assembling template that takes the last JSON array in the reply (tolerating leading prose) and defaults to `[]`. In regression tests assert content (story or section count, closing `</html>`), not just execution status.

## The printed job summary of a push dry run omits scope variables
`push_playbook.sh --brief` prints jobs only; a report template stored as a playbook scope variable does not appear in that summary. After a template edit, diff scope variables as well (see the `diff_playbooks.py` entry above).

## A report that "looks different today" may be instance branding
Instance-level styling (colours) arrives in the trigger payload and overrides the playbook's fallback palette. Check the payload's style block and the instance's branding setting before assuming a playbook change.

## Offline JMESPath testing
Run the Python `jmespath` package with normal Python (an isolated `-I` run cannot see user site-packages). Multiselect-hash keys must be unquoted identifiers (not single-quoted). `contains(string, 'x')` tests substrings and `contains(\`[...]\`, field)` tests list membership. Stub TC-only functions such as `regex` when testing shape expressions.

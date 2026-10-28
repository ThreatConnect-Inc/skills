# Best practices checklist (living list — grow this over time)

Checks to run when **reviewing** a playbook (not just explaining it) — i.e. when a user asks to review/audit/check it, asks what's missing, or asks for improvement suggestions. Each item has a short code for referencing in a review report, what "good" looks like, why it matters (the confirmed failure mode it prevents, where known), and what to recommend when it's missing. Add new items here as new sessions surface new lessons — this list is expected to be incomplete forever, not a finished spec.

## JSON generation (Base Agent jobs whose output is parsed downstream)

**JSON-1 — Explicit "valid JSON only" instruction + OUTPUT SCHEMA block.**
What to look for: a `systemPrompt` with a literal schema example and an instruction like "valid JSON only, no markdown fences, no preamble, no explanation." Why: without this, models readily wrap output in ```json fences or add conversational preamble that breaks a downstream `?eval_json`/parser. If missing: recommend adding both, with a concrete schema example matching the job's actual output fields.

**JSON-2 — "First/last character" instruction.**
What to look for: an explicit instruction that the response's first character is `{` and last character is `}`, with nothing before or after. Why: a cheap, high-value guard against preamble/trailing-text contamination that's easy to miss even when "valid JSON only" is already stated — confirmed as something added independently to one job in one version of a playbook but missing from an otherwise-identical job elsewhere in the same playbook family, suggesting it's not consistently applied even by the same team. If missing: recommend this single line, worded almost verbatim since it's simple and has no real variation worth bikeshedding:
```
Your entire response is a single JSON object. The first character of
your response is { and the last character is }. Output nothing before
or after this.
```

**JSON-3 — BRACKET DISCIPLINE for multi-key/sharded-output jobs.**
What to look for: when a job's `OUTPUT SCOPE` restricts it to a specific subset of keys (see the "OUTPUT SCOPE sharding" pattern in `app_type_cheatsheet.md`), is there explicit guidance against closing the top-level object before every scoped key has been emitted? Why: confirmed failure mode — a model closed the root JSON object right after one key, then appended a remaining key afterward anyway, producing two concatenated fragments instead of one valid object. This is easy to miss because the model's own few-shot schema example can itself be miscopied/misformatted in a way that invites exactly this error (see JSON-4). If missing, recommend:
```
BRACKET DISCIPLINE — read before writing your final closing brace:
A confirmed failure mode: closing the top-level object's final "}"
one key too early — before every key listed in OUTPUT SCOPE has been
emitted — then appending the remaining key(s) after that brace
anyway, producing two concatenated fragments instead of one valid
JSON object.
  - Before writing the FINAL closing "}", re-read OUTPUT SCOPE above
    and confirm every key listed there is present in what you've
    written so far. If any are missing, write them now, inside the
    same object, before closing it.
  - Emit the top-level object's final closing "}" exactly once, as
    the very last character of your output, only after every OUTPUT
    SCOPE key is present.
  - Never place two or more closing braces/brackets on the same line
    with no separation (e.g. "}}"); one per line.
```

**JSON-4 — Schema example formatting consistency (a smell to actually check, not assume).**
What to look for: in a job's own `OUTPUT SCHEMA` example, does every top-level key have *consistent indentation* with its siblings, and does the schema's own closing-brace structure look deliberate (not a dedented/orphaned-looking trailing block)? Why: confirmed — one playbook's schema literally had one key dedented to column 0 with a bare `}\n}` closing, visually looking like a separate trailing document rather than a peer key, and the model's actual output reproduced that exact structural defect (closing early, right before that key). The model wasn't reasoning badly; it was pattern-matching a real formatting bug in its own few-shot example. If found: this is a priority fix, since it's plausibly the literal root cause of a JSON-generation bug, not just a style nit — fix the schema example's indentation to match its siblings.

**JSON-5 — Omit-vs-null convention, stated explicitly.**
What to look for: does the prompt say what to do for absent/empty optional data — "omit the key" vs. "set to null"? Why: a playbook whose whole prompt library consistently uses "omit if absent" can have downstream deterministic code (a hand-rolled JSON serializer in a Template Builder, say) that's simply never been exercised against an explicit `null` leaf, because none has ever existed in the data before. Introducing one nullable field without checking this can break generic downstream processing in a way that looks unrelated to the actual change. If a field is genuinely allowed to be null, cross-check JSON-6/FTL-1 below rather than assuming it's safe.

**JSON-6 — SELF-CHECK checklist scoped to what the job actually owns.**
What to look for: in a multi-worker sharded setup (several near-identical jobs differing only by `OUTPUT SCOPE`), does each job's own `SELF-CHECK` list only reference the keys *that job* actually emits, or is it a blind copy-paste of a master checklist referencing keys other workers own? Why: harmless but confusing — a checklist item checking `ttpMatrix` on a worker that never emits `ttpMatrix` is dead weight that makes the prompt harder to maintain and slightly misleading to read. Low priority, but flag it if noticed.

**JSON-7 — The extractor's model and wording are chosen for raw-JSON reliability, and the parse step is tested against the fenced case.**
What to look for: a small Base Agent whose JSON output feeds a JMESPath/JSON parse job (an intent or entity extractor). Why: a `tc_fast` extractor wrapped its JSON in ```json fences despite "no markdown fences" in the prompt; the parse job failed and the playbook returned an empty body with no error. `tc_balanced` with the full wording (first character `{`, last `}`, "Do NOT wrap it in markdown code fences (no ```json, no ```)", "Do NOT explain") returned raw JSON 4 of 4 times. If missing: use the fuller wording, prefer the balanced model for extractors, and add a guard (an If/Else on a sentinel, or a parse job that tolerates failure) so a malformed reply produces a message, not silence.

**JSON-8 — A "SELF-CHECK before you respond" bullet list can itself cause the prose-leakage it's meant to prevent, especially once a Knowledge/cross-reference step adds task complexity.**
What to look for: a job whose prompt both (a) injects a `#Knowledge:` context block the model is told to cross-reference against (e.g. "check every candidate against this list of existing entities first"), and (b) ends with an open-ended "SELF-CHECK before you respond: did you... did you... did you..." bullet list, rather than concrete examples of the literal final output. Why this matters more than it looks: confirmed root cause of a **silent total-result-loss bug** — once the Knowledge context was present, the model reliably narrated its reasoning in prose before (and around) the JSON answer (confirmed 20/20 in isolated testing with the Knowledge block present, vs. 0/3 without it), violating the "JSON only" instruction. The downstream JMESPath `json_data` parse step does a **strict** parse of the whole string — any leading prose fails the entire parse — and a resilience-oriented `fail_on_jmes_expression=false`/`fail_on_no_results=false` (common elsewhere in a pipeline, see JMES-null-safety items below) swallows that failure into an empty array *silently*, with no error anywhere. This is a materially worse failure mode than the fenced-JSON case in JSON-7: it looks like "nothing in this input qualified," not a parse error, so it can go unnoticed for a long time. The self-check bullet list is a likely contributor, not just an ineffective guard — asking a model to verify several things "before responding" invites it to show that work, even when told not to.
Fix pattern that resolved this (confirmed in production, not just sandbox): replace the open-ended self-check with (1) one line saying the verification is silent and must not be written out, and (2) 1-2 concrete few-shot examples of the *exact terminal output* in the job's real schema, ending immediately before the "now analyze the input below" instruction — mirroring how other reliable structured-output jobs on the same instance are built (dense worked examples ending right at the generation point, not abstract self-check instructions). A tightened `maxOutputTokens` is a reasonable defense-in-depth addition but was NOT the actual root cause here — don't stop at raising/lowering the token budget and assume it's fixed.
How to confirm a fix actually worked, not just looks plausible: (a) test the fixed prompt under **concurrent load** specifically (e.g. 8 simultaneous webhook calls to an isolated sandbox copy), not just serial calls one at a time — this bug's leakage behavior was inconsistent enough that serial sandbox testing alone gave false reassurance both before and after the fix; concurrent load was what reliably separated "still broken" from "fixed" during development. (b) Directly verify the downstream parse step's real tolerance by feeding it a captured real messy response (prose + JSON) rather than assuming how lenient it is — confirmed experimentally that this specific JMESPath app's `json_data` parameter has zero tolerance for any leading text, which was not obvious without testing it directly.
Separate but related, lower-severity pattern confirmed the same session: even well-written prose exclusion rules (e.g. "always drop a victim organization's own domain," "a URL cited as a source is not an indicator") can be followed inconsistently by the model without any JSON-formatting problem at all — this is a plain relevance-judgment reliability issue, and needs the same fix (concrete worked examples matching the exact failing shape, not a restated principle) even when there's no total-failure bug to point to. Note the asymmetry when validating this kind of fix: a mechanical formatting bug (prose breaking strict JSON) reproduces cleanly under the conditions above; a probabilistic judgment lapse on an exclusion rule may NOT reproduce reliably in isolated sandbox testing even with faithful inputs and multiple trials — don't expect a clean "before fails every time, after passes every time" demonstration for this class of fix, and say so plainly when reporting results rather than overclaiming confidence from a handful of clean sandbox runs.

## TQL / fetch jobs

**TQL-1 — `fields=common` requested consistently for Vulnerability/Actor-type queries.**
What to look for: does every fetch touching Vulnerability groups or Actor/Intrusion-Set-type groups request `fields=common`, or only some of them? Why: `fields=common` attaches the platform's normalized `commonGroup` object (CVSS for Vulnerabilities, `priority`/`mitreId` for Threat Actor Profiles) — confirmed easy to add on one fetch (e.g. a top-level query) and miss on a related downstream one, silently losing access to the best available severity/confidence signal for whatever that fetch's content feeds into.

**TQL-2 — Unified-object presence never used as an inclusion/exclusion filter.**
What to look for: does any TQL use `hasCommonVulnerability(...)`/`hasThreatActorProfile(...)` as a hard filter condition on the *primary* result set, rather than purely as a richer-data source once matched some other way? Why: confirmed gap — many real, often high-priority actors (ransomware crews especially) are not MITRE-tracked and have no unified Threat Actor Profile at all; filtering on profile presence would silently and systematically exclude them. Flag this if found — it's a correctness bug, not a style preference.

**TQL-3 — A `resultLimit` cap should have a sort/rank rationale, or at least rely consciously on default ordering.**
What to look for: a fetch with a `resultLimit` but no `sorting` param and no TQL-level quality filter (e.g. a score threshold). Why: without either, a cap just takes whatever the API's default order happens to return (typically `dateAdded` descending) — not necessarily the most severe/relevant items. This isn't automatically wrong (recency can be a perfectly fine signal), but it's worth surfacing as a conscious choice rather than an unexamined default, especially as a fetch's potential match volume grows. Compare against any sibling fetch in the same playbook that *does* have a quality filter (e.g. a `calScore`-style threshold on an IOC fetch) — inconsistency across otherwise-similar fetches is worth flagging even if no single fetch is "wrong" in isolation.

**TQL-4 — Every field a shaping job reads is requested by the fetch that feeds it.**
What to look for: for each fetch job, list the `fields` it requests, then read the JMESPath shaper that consumes it and list the optional fields it reads (`associatedGroups`, `associatedIndicators`, `tags`, `attributes`, `insights`, `common`/`commonGroup`, `linkedGroups`, `threatAssess`, `geoLocation`, `enrichment`...). Why: a field that was not requested simply comes back absent, so the shaper emits null or an empty list with no error. Confirmed: a top-level indicator fetch did not request `associatedGroups`/`associatedIndicators` while its shaper (gated on the user's "include associated data" toggles) read them, so those lists were always empty whatever the user chose. Check every fetch that feeds the same shaper (for example a scheduled-TQL fetch and an Intel-Requirement-results fetch can differ). Note the API rejects some fields per object type (`fields=insights` is valid on groups but rejected for indicators), so check a sample response, not just the field list.

## FTL / Template Builder jobs

**FTL-1 — Recursive serializer helpers guard null at every recursive call site.**
What to look for: a hand-rolled recursive JSON-serialization function (commonly named something like `tojson`) — does it guard with a real `<#if existing??> ... <#else> ... </#if>` before *each* recursive call (inside both its sequence-iteration and hash-iteration branches), not just at its own top-level entry? Why: confirmed failure mode — FreeMarker throws when a function argument resolves to null/missing, at the call site, before the function body's own internal null-check ever runs; a function that looks completely null-safe at a glance can still break on any nullable leaf value reached via recursion. See `references/ftl_debugging.md` for the exact fix pattern.

**FTL-2 — `?eval_json` calls on cross-job string inputs are guarded.**
What to look for: any `<#assign x = someVar?eval_json />` where `someVar` comes from another job's output — is it guarded with `?has_content` (defaulting to an empty collection) rather than called unconditionally? Why: an upstream job/worker legitimately producing no output for a given run (e.g. a parallel worker whose assigned data slice was empty) will pass through as a genuinely empty string, and `?eval_json` on an empty string throws rather than returning something sensible.

**FTL-3 — No `?then(...)` used to guard a potentially-failing call.**
What to look for: any use of `cond?then(possiblyFailingExpr, fallback)` where `possiblyFailingExpr` would itself throw if `cond` is false. Why: `?then` is not short-circuiting in FreeMarker — both arguments get evaluated regardless of which one is selected, so this pattern doesn't actually guard anything; only a real `<#if>/<#else>` block does. See `references/ftl_debugging.md`.

**FTL-4 — Reuse existing base-URL/origin-style variables before adding new ones.**
What to look for: does the template already compute a UI base-URL/origin value (often from stripping a trailing `/api` off an API-base input) that a new feature could reuse, before a new unbound variable gets introduced for the same purpose? Why: confirmed — a new feature referenced a variable that was never actually wired as a job input, when an equivalent, already-correctly-computed, already-in-scope variable existed a few lines above in the same template.

**FTL-5 — Report templates are laid out for the viewer's pagination, not for CSS print rules.**
What to look for: a report/HTML template that relies on `page-break-*` / `break-*` CSS, or puts a section title and its content as separate sibling blocks. Why (confirmed against the TIP AI report viewer, verify against the current viewer): pages are fixed 8.5 x 11 in; each top-level `<section>` starts a new page; inside one flowing section, direct-child blocks are placed whole, greedily, and CSS break hints are ignored; tables taller than about 950px are flattened (a fix for long tables is expected; flattening replaces the whole table with its text inside a class-less `<div>`, and in one test 1 and 3 one-line rows survived while 5 to 10 rows of long unbroken strings such as file hashes did not, even when the table fit on one page). Consequences: (a) wrap eyebrow + heading + content of each section in ONE block so a title is never stranded at a page bottom; (b) to force a page break (e.g. start "Recommendations" on a fresh page) close the current top-level `<section>` and open a new one, and remember CSS keyed to the old `id` must also cover the new one (`:is(#a,#a-2)`); (c) big atomic blocks (long lists, source lists) leave white space, so cap or split them; (d) measure rather than guess: per-page block heights via the editor iframe (see `dataminr-playbook-qa`); (e) to prove where markup was lost, compare the template job's own output (valid `<table>` present?) with the viewer DOM: if the playbook output is fine the defect is in the viewer layer and no prompt or template edit will fix it, only reducing the table's height or using a div-based component such as a rated list.

## State / DataStore jobs

**DS-1 — A DataStore read never references `datastore.data.string` directly.**
What to look for: a job downstream of a `TCPB - DataStore v4` GET — does it reference `datastore.data.string` directly, or does it go through the always-populated `datastore.response.json` plus a JMESPath extraction (`_source.data || ''`)? Why: confirmed crash — `datastore.data.string` is left completely UNDEFINED (not merely empty) when the record doesn't exist yet, and referencing it anywhere downstream hard-crashes the whole run with no useful error. This is exactly the failure mode a first-ever run (no watermark/cursor written yet) will hit. If missing: flag as a crash risk on the very first run against a fresh key.

## JMESPath / parallel-array jobs

**JMES-1 — Parallel `StringArray` outputs are built with `map()`, not a bare projection.**
What to look for: when a JMESPath job builds several same-length `string_array_expressions` meant to feed an Iterator's `array_inputs` in lockstep (e.g. an array of ids alongside an array of names from the same source array), are they built with `map(&expr, arr)` rather than `arr[*].expr`? Why: confirmed — a plain `[*]` projection silently DROPS any element whose referenced field is null/missing, breaking index alignment between the "parallel" arrays (a 2-element source array with one missing field produced a 1-element projected array). `map()` preserves every element regardless of missing fields. If missing: a silent count/alignment bug is likely whenever the source data can have an item with an optional field unset — which is common.

**JMES-2 — Aggregations and key-picking over optional fields are null-guarded.**
What to look for: `max_by`/`min_by`/`sort_by` whose key expression can be null for some item, and `include_keys(x, ...)` (or any function that requires an object/array) applied to a path that can be absent. Why: these raise "invalid type for value: None" instead of skipping, and the crash depends on the record shape, so it passes on one sample and fails on the next (confirmed: `include_keys([0].geoLocation, ...)` died on a File indicator because only IP/host indicators carry geo data; `max_by(@, &threatAssessScore)` fails the same way for any copy without a score). Fix: `include_keys(not_null(x, \`{}\`), ...)`, `max_by(@, &not_null(f, \`0\`)).f`. Test with a sample that contains every record shape the job will meet (every indicator type, items with and without each optional field), using `scripts/jmespath_local_test.py`, then confirm in a sandbox playbook because the TC-specific functions are only approximated offline.

**JMES-3 — Consolidating records across owners keeps traceability and dedupes the lists inside them.**
What to look for: a job that merges copies of the same entity (same indicator value or group name from several owners) with `group_by(data, &key) | values(@) | map(&{...}, @)`. Why: the consolidated object has no single `id`/`webLink`/`ownerName` any more, so downstream steps that build links or `sources` lists lose them unless the job carries `sources: map(&{ownerName: ownerName, dateAdded: dateAdded, id: id, webLink: webLink}, @)`; and nested association lists are repeated once per owner copy (a sample showed the same group listed twice), so dedupe them on id (`group_by(@, &to_string(id)) | values(@) | map(&[0], @)`) and cap them. Gather nested `data` arrays with `compact(map(&associatedGroups.data, @)) | flatten_list(@)`. Downstream code that read `id` must read `sources[0].id` instead.

**JMES-4 — `strip_quotes` is `true` on every JMESPath job whose outputs are plain strings that are reused.**
What to look for: JMESPath jobs with `strip_quotes` `false` that emit ids lists, counts, names or sentinels used later in a TQL string, an `equals` check or a prompt. Why: with `false` the stored value keeps its surrounding quotes (`"123,456"`, `"0"`), so a later `id in (...)` fails or an `equals 0` never matches, and the run dies silently (empty webhook body). `true` removes only the surrounding quotes and left JSON arrays/objects intact in a confirmed run. If wrong: set it to `true` and re-read one output through a truncated debug build.

## Batch Import jobs

**BATCH-1 — Guard against a fully-empty Batch payload.**
What to look for: is there anything upstream of a `TCPB - ThreatConnect Batch Import v2` job guaranteeing `import_data` is never `{"group":[],"indicator":[],"association":[]}` (or empty-equivalent) on a run that happens to have zero new items? Why: confirmed hard crash — a fully empty payload, even a literal `{}`, causes a silent, unrecoverable failure (empty webhook body, no error surfaced anywhere). If the use case can legitimately produce zero new items on some runs (e.g. a time-gated sync with nothing new since the last watermark), this is a real and likely-to-be-hit gap, not a theoretical one — flag it even though no generically confirmed fix exists yet (consider an If/Else short-circuit on a zero-count check before the Batch job).

## Architecture / hygiene

**ARCH-1 — "Copy of X"-style duplicate jobs are intentional and traceable.**
What to look for: near-identical jobs (same app, same params) that aren't obviously commented/named to indicate which `If/Else` branch each belongs to. Why: these are commonly one job per mutually-exclusive branch (not dead duplicate work), but an unlabeled "Copy of X" is a maintenance trap for the next person (or session) to misread as redundancy and delete, or to edit only one copy of a pair that needs to stay in sync. Recommend a naming/comment convention making the branch association explicit.

**ARCH-2 — No leftover/dead code from an abandoned or reverted feature.**
What to look for: CSS, markup, or prompt instructions clearly built for a feature that isn't actually wired up / doesn't do anything (e.g. a `@page` print-orientation rule with no actual print pipeline honoring it; a class added only to support a rule that was supposed to be removed). Why: confirmed real case — a revert was requested and only partially carried out, leaving confirmed-non-functional CSS live in a playbook for an extended period without anyone noticing, since it caused no visible error, just silent dead weight. Flag anything that looks like it was built for a feature the playbook doesn't currently appear to use.

**ARCH-3 — Deterministic joins/lookups aren't delegated to an LLM job.**
What to look for: a Base Agent job whose job includes matching/joining two lists (e.g. matching a code against a lookup table to attach a corresponding id). Why: confirmed unreliable even with a clear, explicit instruction — most items came back unmatched despite real matches existing in the data. Recommend doing this kind of join with JMESPath (or another deterministic step) before the data reaches any Base Agent job, so the LLM only ever passes an already-resolved field through.

**ARCH-4 — Fan-in (branch convergence) is not assumed to work; fan-out is.**
What to look for: does the design have two or more mutually-exclusive branches (`If/Else` Pass/Fail, or similar) reconverging on one shared downstream job? Why: confirmed broken on at least one real instance (instance C), in three different shapes — a plain downstream job, a dedicated `Merge` app, and a full production design — all using the same pattern. Each branch worked perfectly alone; the shared downstream job simply never fired either way. The same shape is documented working on a different instance (instance A) elsewhere in this project, so this is platform/instance-dependent, not a universal rule — but exactly the kind of thing to smoke-test in isolation on a new instance before relying on it, rather than assuming it will "just work" because it worked somewhere else. Fan-out (one job's Pass driving multiple independent downstream branches that never rejoin) is unaffected and confirmed reliable everywhere tested; recommend redesigning around fan-out where the converging branch isn't strictly required to gate the main response.

**ARCH-5 — A file/binary payload relayed between jobs never passes through a `body`-type HTTP parameter.**
What to look for: a chain that fetches raw file/binary content via one HTTP-style job and forwards it (via a job-output reference) into another job's `body` param. Why: confirmed byte-level corruption — referencing a String-typed output into ANY job's `body`-type parameter applies JSON-string escaping to the actual bytes sent (wraps the value in quotes, escapes embedded `"`), with no reliable way to reverse it at scale. The same value referenced directly into a trigger's `httpResponseBody` is unaffected. If a playbook needs to carry file/binary content between jobs (e.g. syncing an attached document from one TC instance's Group to another's), it should route through `TCPB - Binary Operations v2` ("Convert from String") into a `Binary`-typed param (e.g. `file_content` on `Update Groups`) instead of any `body` field.

## Attribute-write safety

**ATTR-1 — Generated/long text written into an attribute is checked against that attribute type's `maxSize`.**
What to look for: a Base Agent (or any job whose output size can scale with its input — a Markdown/HTML conversion, a generated summary, anything that might carry embedded binary like base64 images) feeding a `TCPB - Threatconnect Attributes v2` job's `attribute_values`, with nothing upstream bounding how large that value can get. Why: confirmed gap — `GET /api/v3/attributeTypes` returns a `maxSize` (character limit) and `allowMarkdown` flag per attribute type (e.g. `Description` had `maxSize: 102400` on one instance), and nothing in the Attributes app itself guards against exceeding it; a real report's embedded images alone totaled ~433KB of base64, over 4x that limit, found only by direct measurement of real sample data, not by any error the pipeline surfaced on its own. If missing: recommend querying `/v3/attributeTypes` for the actual limit early in the design (not after a write starts silently truncating or failing), and either bounding the generated content's size explicitly or routing anything that can't fit to a different mechanism (see CONV-2 below for the binary case specifically).

## Content conversion (HTML -> text/Markdown) jobs

**CONV-1 — An HTML-to-text/Markdown conversion checks for print-pagination content duplication before trusting a flat read of the DOM.**
What to look for: does the conversion job's prompt (or any deterministic pre-processing) account for the possibility that the source HTML renders its content more than once — once in a primary flowing container, and again split across page-break/print-layout elements (a pattern seen in a real report export: paragraphs and images repeated verbatim inside elements like `reportpage-text-block`, separated by `reportpage-divider` dividers)? Why: confirmed real case — a naive conversion would double every duplicated passage (and every duplicated embedded image) in its output. This is a general risk for any HTML export designed for both screen and print rendering, not unique to one report template. If missing: recommend either a deterministic de-duplication pass before the content reaches an LLM, or (more robust against layout variation) an explicit instruction in the conversion prompt naming the specific duplication pattern observed and telling the model to emit each distinct passage exactly once in original reading order.

**CONV-2 — Binary content embedded in the source HTML is kept out of the LLM's context via a deterministic placeholder/splice pattern, not inlined into the prompt or asked of the model to reproduce.**
What to look for: a conversion job whose input HTML contains embedded binary (most commonly `<img src="data:...;base64,...">`) — is the raw binary ever sent into the model's prompt, or worse, is the model asked to reproduce it verbatim in its output? Why: large base64 blobs bloat prompt/output token usage for no benefit (a model has no reason to "understand" image bytes to do a format conversion), and asking a generative model to reproduce a large exact string verbatim is an unnecessary reliability risk for something that's actually a deterministic copy operation. The confirmed-sound pattern (reasoned from direct measurement of a real case — image content alone exceeded the target attribute's size limit, see ATTR-1 — though not yet verified end-to-end in a live run): extract each embedded binary's data deterministically into an array before the conversion job runs, replace its occurrence in the HTML with a short placeholder token (e.g. `[[IMG_0]]`); instruct the model only to carry each token through verbatim to the corresponding position in its output; then splice the real data back in with a final deterministic Find/Replace or small `Iterator` keyed by index, after the LLM call completes. If missing: recommend this pattern over either dropping images or inlining their binary through the prompt.

## Entity/IOC extraction from narrative text (precision-backstop LLM jobs)

Confirmed over a 3-round adversarial QA campaign (15 real reports, re-validated after each fix) on
a pipeline where a secondary LLM agent double-checks/supplements a primary context-blind extractor
(e.g. a MITRE-bound or regex/NER-based tool) for named threat actors, malware, and IOCs. These
patterns generalize to any "read narrative text, decide which named things are actually worth
tracking" extraction job, not just this one domain.

**EXT-1 — The relevance bar is substantive discussion, not mere mention.**
What to look for: a prompt that extracts any name/value the text contains, with no filter for HOW
it's mentioned. Why: confirmed failure mode — a context-blind extractor (or an under-specified LLM
one) will grab a name from a comparison ("unlike APT28..."), an unsubstantiated third-party claim,
a historical aside, or a quoted vendor/researcher's own brand, none of which the report is actually
analyzing. Fix: require the report to do real analytical work ON the candidate (background,
attributed activity, assessed capability, a dedicated finding) before extracting it, with explicit
negative examples for each of the patterns above — generic language is not enough, the exact
phrasing patterns that slip through need to be named (see EXT-4).

**EXT-2 — A report's own structured labeling overrides the depth-of-discussion bar.**
What to look for: a candidate that gets only one line of prose but is explicitly type-labeled by the
report itself (e.g. a table row marked "Threat Actor"). Why: confirmed — a relevance filter tuned
against name-drops will also wrongly reject entities the report's own author has already determined
are worth tracking, just because their individual prose treatment is brief. Fix: an explicit
carve-out that a report's own structured table/list labeling satisfies relevance on its own,
regardless of prose depth — scoped only to genuinely structured, explicitly-labeled entries, not a
general loosening of the bar.

**EXT-3 — Personas, named sub-units/cells, and independent outside/rival actors are each their own
entity, separate from any collective they belong to or comment on.**
What to look for: a report describing a named collective where an individual leader/persona, a
named sub-unit ("cell", "channel"), or a separate disputing/rival persona each have their own
described activity — does the extraction stop at the collective's name and never surface these?
Why: confirmed — a model will readily fold an individual's extensively-described actions into "the
collective did this" and never extract the individual, even when the individual is the one actually
posting/claiming/operating. The fix generalizes across all three sub-cases (an individual lead, a
named cell with its own observed activity, an outside persona who independently disputes or
undermines the main subject) — the common test is always "is there a specific action independently
attributed to this exact name," not "is this name part of or about the main collective." Watch the
inverse failure too: a name that gets an organizational *role* assigned to it by someone else's
claim ("X serves as the collective's High Command") but never itself does anything is NOT the same
as independent activity — confirmed overshoot when a persona/cell rule was worded broadly enough to
catch role-assignment-only mentions.

**EXT-4 — Guilt-by-association: being named near the real subject is not itself qualifying activity.**
What to look for: constructions like "a community loosely associated with X, Y, Z" or "presumably
the chat with X and Y" — X/Y/Z get named, and the association itself may be stated as fact, but
the TEXT never attributes any independent action to them. Why: confirmed — this is one of the
hardest patterns to get a model to reject consistently; a generic instruction ("don't extract from
association alone") caught some instances but missed others with near-identical phrasing, and only
a worked example closely matching the EXACT phrasing that slipped through reliably fixed it. If this
pattern is suspected, don't assume one generic rule will generalize — test the specific phrasing
that's failing and add a worked example modeled on it, not just a restated principle.

**EXT-5 — An "existing known entities" reference list changes NAMING only, never WHETHER to extract.**
What to look for: a prompt that gives the model a live list of entities already tracked by the
instance (e.g. via a Knowledge/DataModel context, see `app_type_cheatsheet.md`'s Base Agent entry)
so it can recognize an alias and avoid creating a duplicate under a new name. Why: confirmed
failure mode — once an entity from an EARLIER run of the same report exists in that list, a later
re-run of the identical report can start omitting it entirely, as if "already tracked" meant
"nothing new to report," which silently breaks re-association of a known actor with every future
report that discusses them (defeating much of the point of running this pipeline repeatedly). Fix:
an explicit, unambiguous sentence that being already-known is never a reason to omit an entity —
the list only determines which exact string to output for it, never whether to output it at all.

**EXT-6 — A victim organization's own domain/infrastructure is never an IOC, even on a claimed-but-
unconfirmed compromise.**
What to look for: a report naming a victim's real domain as the target of a CLAIMED breach/leak,
with the claim never independently confirmed — is that domain still being extracted as an
indicator? Why: an IOC exists to help detect the ATTACKER's activity (delivery infrastructure, C2,
phishing lookalikes, a specific asset the attacker has actively repurposed) — being victimized does
not make an organization's own brand domain something to "watch out for," and loosening this only
for "confirmed" compromises isn't tight enough, since a report can describe an actor's claim as
credible without the report itself ever confirming it. Fix: drop a victim's own domain
unconditionally, with a narrow named exception only for a specific technical sub-asset (not the
main domain/brand) the report shows the attacker has actively repurposed for ongoing malicious use.

**EXT-7 — Citation/reference links are incidental to the report, not evidence of attacker
infrastructure.**
What to look for: URLs in a "Resources," "References," or "Further Reading" section — a vendor
advisory, a news article, a victim's own breach-disclosure post, a researcher's write-up or PoC
repo. Why: confirmed real case — 100% of a report's extracted IOCs turned out to be exactly this
category (every one a citation, none attacker-controlled), because the extractor had no explicit
rule distinguishing "this is where the report's information came from" from "this is attacker
infrastructure the report found." This holds even when the linked page is genuinely about the same
incident.

**EXT-8 — Pattern-consistent-list recognition has a format blind spot: prose runs vs. tables.**
What to look for: a fix aimed at a run of same-pattern values won't necessarily catch the identical
values when they instead appear as one column in a table with other columns (dates, IPs, ASNs,
registrars) interleaved between rows. Why: confirmed — a fix worded around "values listed back-to-
back with no other text between them" fully resolved the prose-run case (recovering a short,
word-like value that read more like ordinary English than a domain, e.g. one short string resembling
a plain English phrase, surrounded by clearly domain-shaped siblings) but had zero effect on the
same underlying gap in a report whose IOC listing was a Markdown table instead. If a report's
format varies (prose list vs. table), test and likely word the fix separately for each — a fix
validated on one format is not confirmed for the other.

**EXT-9 — Isolated/sandbox testing of an agent that normally receives a large upstream context
(e.g. a primary extractor's full raw output) needs that real context, not a hand-built stub, to be
trustworthy.** What to look for: a fix "validated" by feeding the agent only the report text plus a
small manually-constructed candidate list, then deployed on the strength of that isolated pass. Why:
confirmed twice in the same campaign — a fix that passed 3-for-3 in isolated testing failed
identically to before in the live pipeline, in both cases because the sandbox's hand-built stand-in
for the upstream context was far smaller/simpler than what the real pipeline actually passes, and
that size/shape difference materially changed the model's behavior. Treat an isolated-sandbox pass
as provisional until confirmed by a real end-to-end run, and prefer running the actual upstream app
(e.g. the real extraction/classification app) inside the sandbox over approximating its output by
hand, whenever the job under test depends on that upstream content in a way that's hard to fake
faithfully.

## Trigger payload handling (agent / webhook playbooks)

The first job after an agent or webhook trigger is usually a JMESPath "extract config" job that reads fields from the payload the UI or caller sends. The UI is owned by someone else and changes without notice (a key dropped, renamed, or replaced by a reference). Run `scripts/payload_contract_check.py <playbook.json> <sample payload>` to list every key that job reads, which are missing from a payload, and which of those reads are unguarded.

**PAY-1 — Every payload read tolerates a missing key.**
What to look for: expressions that pass a payload field straight into `join()`, `length()`, `in()`, `contains()`, `sort()` or a filter projection with no `|| <default>`. Why: a missing key is null, and those functions raise "invalid type for value: None", which kills the whole run before any real work (confirmed: a report agent died in its config-extract job when the UI stopped sending `additionalData`, `resultLimit` and `style`). Fix: `join(',', (additionalData || \`[]\`)[?...])`, `contains(additionalData || \`[]\`, 'x')`, `resultLimit || \`1\``. Optional keys always get a default; required keys get a clear failure message instead (see the debug-branch pattern in `dataminr-playbook-builder`).

**PAY-2 — `to_string(<missing>)` is not guarded by `||` elsewhere in the chain.**
What to look for: `to_string(x.y)` used to build a downstream parameter. Why: it returns the text `"null"`, not an empty value, so a logo id, style object or filter string silently becomes the literal word null and travels downstream (a broken asset reference, or the text "null" inside a prompt). Fix: `x && to_string(x.y) || ''`.

**PAY-3 — Enumerated labels from the UI are normalized once, at the boundary.**
What to look for: prompts or templates that match an exact label ("Executive Brief") while the UI sends variants ("ExecutiveBrief", "Weekly Operational Report", "Technical Analysis"). Why: a variant silently selects the default behaviour (a 15-page Deep Dive instead of the intended format) with no error. Fix: map to one canonical value in the extract job (lower-case, strip spaces, `contains`) and let every later job match only the canonical value. Cheap audit: take each dropdown label and grep every prompt/template for it.

**PAY-4 — The payload contract is written down and re-checked.**
What to look for: a saved sample of the real payload (and the key list the extract job reads) in the project. Why: with no record there is nothing to diff when the UI changes. Re-run the contract check whenever someone reports a failure in the extract job, and paste the offending payload in.

## Multi-step LLM pipelines (several Base Agent jobs)

**LLM-1 — Each worker is actually passed every input its prompt mentions.**
What to look for: for each Base Agent, list the inputs its system prompt refers to (`reportFormat`, a limit, a mode) and confirm each appears in its user prompt / inputs. Why: confirmed: two of three parallel workers referred to `reportFormat` but never received it, so their format-specific rules never fired. Include the user's free-text guidance/intent in this audit: it was passed only to the planner while the content workers' prompts referred to "the intent input".

**LLM-2 — A deterministic check sits between LLM hops.**
What to look for: LLM output parsed by the next job with no existence check. Why: model output is non-deterministic (the same input failed once and passed on re-run). A JMESPath/template check that required keys exist, with a degraded path, turns a whole-run failure into a smaller one.

**LLM-3 — Downstream counting and templating tolerate sections a format omits.**
What to look for: `length(x)` or `x.y` on keys that only some formats produce. Why: adding a format that omits sections broke the existing content-extract job (`length(null)`). Fix: `length(x || \`[]\`)` throughout, and `?has_content` guards in the template.

**LLM-4 — No cadence or time wording is hard-coded into prompts** ("weekly", "this week", "daily") unless the data window dictates it. Report windows are chosen by the user; the label text leaks otherwise.

**LLM-5 — The primary subject reaches the LLM workers as content, not just as ids.**
What to look for: an agent whose user picks a set of objects (a TQL result, a group, an indicator set) but whose pipeline only uses that result to build an id list for further fetches. Why: confirmed — the context fetches returned objects *associated with* the selection, so the selected objects themselves (the AI `insights.summary`/`bullets` of Report and Event groups, an indicator's scores and owners) never reached any worker. Fix pattern: (1) shape the top-level result into its own block, labelled as the primary subject, and keep associated blocks as context; (2) carry association stubs (`{id, name or summary, type}`) on each object, gated by the user's "include associated data" toggles; (3) join stubs to full objects by id deterministically (ARCH-3) and tell the workers that stubs without a matching full object may be named but not described; (4) put the basis (what kind of object was selected), the criteria/TQL, the time scope, returned-versus-limit (so truncation can be reported) and the user's guidance in a header; (5) tell every worker how to read each block per basis, and make statistics (counts, type breakdowns, daily counts) come from the right set for the basis.

**LLM-6 — A new content domain is added everywhere the vocabulary lives.**
What to look for: when a report pipeline gains a section or data domain, every place that enumerates domains: each content worker's schema and rules, the content-flag/count extraction, the planner's valid `contentKey` list, ordering rules and component mapping, the section builder's rule for the chosen component, the template branch, and the sources list. Why: the vocabularies are closed, so a key missing from one place is silently skipped, planned but empty, or mapped to the wrong component. Fix: after the edit, search the whole definition for the new key and confirm each place; gate optional domains in the planner by explicit conditions (e.g. only for one basis, or when the guidance asks for it) so existing report types do not change.

**LLM-7 — Counts and totals are computed deterministically and passed in, never recounted by the LLM.**
What to look for: prompts that ask the model to say "showing X of Y" or to compare shown and total. Why: a model told to report how many techniques it was shown said 155 when the list held 150. If missing: have the shaper emit `to_string(length(data || \`[]\`))` and, with `count=true` on the fetch, `to_string(count || \`0\`)`, put both in the user prompt, and tell the model to quote them exactly and never recount.

**LLM-8 — Anything countable, placeable or checkable is done by a deterministic stage, not a prompt rule.**
What to look for: prompts that ask the model to hit a story total, merge or not merge items, route items to sections, or drop empty sections. Why: confirmed across several versions of one report agent, rule compliance flipped between renders of identical input. Fix pattern: a precompute job (grouping keys, promotional flags, clusters), a fallback-content job built from the items' own fields, and an assembler that places, backfills and lists leftovers; the LLM only writes prose per cluster. Label machine-built content visibly.

**LLM-9 — Review each rule-following worker's `languageModelConfiguration`.**
What to look for: temperature, topP and `maxOutputTokens` sitting next to the prompts. Why: a synthesis worker with a low token cap that narrates before its JSON runs out mid-sentence and breaks the downstream `?eval_json` (see gotchas). Use a low temperature for rule-following workers, a generous cap, and "work silently, output only JSON" in both prompts.

## How to use this when reviewing a playbook

For each Base Agent job: check JSON-1 through JSON-6 against its `systemPrompt`. For each fetch job: check TQL-1 through TQL-4. For each Template Builder job: check FTL-1 through FTL-4 against its `template`. For each `DataStore` job: check DS-1. For each JMESPath job feeding an Iterator: check JMES-1; for every JMESPath shaper: JMES-2, JMES-3 and JMES-4. For each `Batch Import` job: check BATCH-1. For each job writing into an attribute: check ATTR-1. For each HTML-to-text/Markdown conversion job: check CONV-1 and CONV-2. For each named-entity/IOC extraction job (especially a precision-backstop agent paired with a primary extractor): check EXT-1 through EXT-9. Check PAY-1 through PAY-4 on the job that reads the trigger payload, LLM-1 through LLM-6 on any pipeline with more than one Base Agent, FTL-5 on report templates. Check ARCH-1 through ARCH-5 across the whole job graph. Report findings grouped by category, each as present/missing/partial with the job name(s) involved — don't silently assume something's fine just because it wasn't flagged as broken; this list only covers what's been confirmed so far, not an exhaustive standard.

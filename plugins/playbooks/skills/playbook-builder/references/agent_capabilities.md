# Giving a Base Agent tools, Knowledge and AI Hybrid Search

How to add the three ways an agent can get at data it was not handed in its prompt: tools it calls itself, Knowledge items the platform fills before the call, and the AI Hybrid Search app step. Shapes below were read from exported playbook definitions and confirmed by pushing and running them (Nov 2026); recheck after platform updates. For what each app does and its outputs, see `playbook-explorer/references/app_type_cheatsheet.md`.

## Which one to use

| Need | Use |
|---|---|
| Data you always need, in a known shape, before the model runs | A fetch or search app step plus JMESPath, then pass the result in the prompt. Most control: you can sort, filter, merge and cap it. |
| A simple "give the model the search results for this query" | A Knowledge item on the agent (no extra steps, but you get less control, see below) |
| Data needed only for some questions, or for records the model picks after reading the first results | An agent tool |
| An action (send an email, call an API) | An agent tool, tested while the playbook is inactive or against a sandbox |

## 1. Agent tools (`agentTools`)

Each Base Agent job has an `agentTools` array (and a `toolsets` array, only ever seen empty; its use is unconfirmed). An entry is:

```json
{"name": "threatconnect_api",
 "appCatalogItem": {"id": "<instance-specific>", "programName": "TCPB - ThreatConnect API v3", "displayName": "ThreatConnect API", "programVersion": "3.0.3", "runLevels": [{"runLevel": "Playbook"}]},
 "outputVariables": "[ ... ]"}
```

- `name` is the tool name the model sees. Seen: `threatconnect_api` (ThreatConnect API v3 app) and `send_email` (Send Email v3 app).
- Do not hand-write the `appCatalogItem` block: catalogue ids and versions differ per instance. Copy the whole entry from an export that already has the tool, or ask the user to add the tool once in Designer and fetch it. When copying across instances, drop the `id` on each `runLevels` entry (the push accepted that). Then check the fetched definition after the push.
- Tell the model in the system prompt when to call the tool, the exact URL pattern, a call cap, and what to do if a call fails or a field is missing. For the API tool, the query string goes inside `url`; a separate `params` argument is ignored (see the cheatsheet).
- Cost and behaviour seen: median about +1 s per answer (range about -1 to +7 s); 0 to 7 calls per question depending on the question; one combined TQL call per record type (`id in (...)`) is cheaper than one call per record. The calls show up as extra executions of the run.
- **A new tool block in a prompt can change unrelated output.** Adding a lookup block for one record type made one other question type lose its opening summary line in 2 of 2 runs. Regression-run questions that should not use the tool, not only the ones that should.
- A tool that sends or changes something does it for real. Keep such an agent inactive or in a sandbox playbook until the call is verified.

## 2. Knowledge items (`userContext`)

The `userContext` parameter is a JSON string holding a list of items. Copy an existing item and edit it rather than building one from nothing.

- `knowledgeType: "DataModel"` runs a live search before the model call. `searchType` is `TQL`, `Keyword` or `AiSearch`; `dataModelType` is the object scope (for example `Groups`, `AllObjects`). For `TQL` the `key` is the TQL; for `Keyword` and `AiSearch` the `key` is a variable reference to the query text (for example `#App:<id>:agent.out!String`).
- `value` is the description the model sees for that result set ("keyword results, no score" and so on). Write it; the model uses it to weigh the set.
- `variableName` names the set. Reference it in a prompt as `#Knowledge:<jobId>:klg.datamodel.<variablename lowercased>!String`, where `<jobId>` is the agent job's own id.
- `results` options: `includeTags`, `includeThreatRating`, `includeConfidence`, `includeAssociatedGroups`, `includeAttackTags`, `attributeTypes`, `limit`, `maxAssociations`, plus `similarityScore` on `Keyword`. Booleans in these options were seen as the strings `"true"`/`"false"`.
- `dateAddedMin` / `lastModifiedMin` take a variable reference, epoch milliseconds, or empty (no filter). Words such as "in the last 60 days" appended to the query are not a filter.
- `knowledgeType: "Playbook"` passes a playbook variable (for example a `#Global:` binary holding a template) to the model with a `value` description.
- Several items on one agent work. Each set is separate: the same record can appear in two of them and nothing de-duplicates, so tell the prompt to treat the same id as one item. `AiSearch` results carry a relevance score; `Keyword` results do not.
- Limits seen: `AiSearch` returned about 16 results when 25 were asked; ranking is by relevance, not date, so a generic question can fill every slot with older near-duplicates; and the item returned no association fields for records that had associations in the AI Hybrid Search app. To see what the model actually received, use DEBUG/TRACE logs (`execution_logs.md`, "Knowledge value").

## 3. The AI Hybrid Search app step

Catalogue entry: `programName` "AI Search", `displayName` "AI Hybrid Search" (version 1.2.1 seen), run level `Playbook`. Parameter names as stored in a job (booleans are the strings `"true"`/`"false"`, dates are epoch ms):

`query`, `mode` (`Basic`/`Advanced`), `searchType` (`AiSearch`), `domain` (the Type: for example `Groups`, `All Objects`; accepts a variable), `owner`, `resultLimit`, `dateAddedMin`, `lastModifiedMin`, `minRelevance`, `includeTags`, `includeAssociatedGroups`, `includeAssociatedIndicators`, `includeAttackTags`, `attributeTypes`, `maxAssociations`, `includeThreatAssess`, `includeCommonData`, `includeMetadata`, `failOnDegraded`.

- **New parameters are missing from a stored job until the job is saved once in Designer.** A push of a definition fetched before an app update left the new settings absent; save a draft in the UI, fetch it, and read the exact names back from that.
- `includeThreatAssess` adds `threatAssess` (score, priority, rating, confidence) to Indicator records; `includeCommonData` adds `cvss` (v3.x and v4 scores and severities) and `kev` to Vulnerability records and `aliases`/`mitreId` to Group records. Case records come back with `dataType` Case and a workflow web link.
- An invalid `domain` string returns an empty response, not an error. Validate it upstream (a parse or branch step).
- Prefer the app over a Knowledge item when you need control: separate windows (all-time and recent branches run in parallel), sorting newest first with a deterministic step, thresholds, merging, and association fields. Prefer the Knowledge item when the raw result set straight into one agent is enough.
- Timing: about 7 to 10 s for one search alone, up to about 30 s with several playbook runs at once. Run independent searches in parallel branches.
- Results depend on the query text: a short entity-only query scores far higher than the same topic inside a long question. Have an upstream step rewrite the question into a search string, and set `dateAddedMin` from a date step, since ranking ignores date.
- To compare search settings without generating answers, use the retrieval-eval echo harness (`SKILL.md`; scoring in `playbook-qa`).

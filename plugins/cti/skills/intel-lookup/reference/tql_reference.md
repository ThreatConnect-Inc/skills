# TQL Reference (verified)

TQL (ThreatConnect Query Language) is used as the `tql` parameter on `tc_list` (MCP) or the `tql=` query string parameter on the direct v3 REST API. **The keyword you filter on is often not the same as the field name in the JSON response.** This file records what's been confirmed live; extend it as new keywords are verified rather than guessing.

## Confirmed keywords

| Resource type | Filter intent | TQL keyword | Notes |
|---|---|---|---|
| `indicators` | Filter by indicator type (Address, Host, File, URL, etc.) | `typeName` | **NOT `type`** — `type` is a numeric type-ID field; passing a string to it fails with `"Expected type Integer, found type String"`. Confirmed live. Same `typeName`-not-`type` pattern as `groups`. |
| `indicators` | Batch-match multiple exact values at once | `summary IN ("val1", "val2", ...)` | Confirmed working — batches multiple exact-value lookups into one query instead of one call per value. An IOC not in TC simply doesn't appear in results, no error. |
| `groups` | Free-text search of the display name/title | `summary` | **NOT `name`** — `name` fails with "not a known parameter" even though `name` is the JSON field returned. |
| `groups` | Filter by group type (Report, Adversary, Vulnerability, Incident, Malware, Event, Document, etc.) | `typeName` | **NOT `groupType`** — `groupType` fails. `typeName EQ "Report"` confirmed working. |
| `groups` (Vulnerability type specifically) | Match a specific CVE | `summary EQ "<CVE-ID>"` | Prefer `EQ` over `CONTAINS` when `typeName EQ "Vulnerability"` — a Vulnerability group's `summary` is always exactly the CVE ID (e.g. `CVE-2026-76460`), never free text, so an exact match is correct and faster. Keep `CONTAINS` for `Report`/`Event`/other free-text-titled types, where the CVE ID is embedded in a longer string. |
| `groups` | Filter/scope by owner or source feed | `ownerName` | Confirmed working, e.g. `ownerName EQ "CAL Automated Threat Library"`. Useful for isolating one feed's contribution when consolidating a multi-source result set. |
| `groups` | Filter by exact ID(s) | `id` | Confirmed working, e.g. `id EQ <group-id>`, and combinable with `OR` for a small set of specific IDs. |
| `indicators` | Free-text search of the indicator value | `summary` | Same generic keyword as groups. Confirmed against IP indicators. |
| `indicators` | Active/inactive status | (auto-applied) | The MCP server appears to auto-inject `indicatorActive=true` into indicator TQL by default — visible in the returned pagination `next` URL. If you need inactive/expired indicators too, this default may need to be explicitly overridden; hasn't yet been confirmed how — test before relying on it. |

## Confirmed operators

- `EQ`, `CONTAINS`, `!=` — confirmed working. The TQL spec documents `!=`/`NE` as the negation operator and `EQ`/`==`/`EQUALS` as equality, `GT`/`LT`/`GEQ`/`LEQ` as comparison, `LIKE`/`STARTSWITH`/`ENDSWITH` as pattern matches, and `NOT` to negate `IN`/`LIKE`/`CONTAINS`/`STARTSWITH`/`ENDSWITH` or a nested query.
- `NEQ` — **confirmed NOT a valid operator** (rejected with `"'NEQ' is not a valid operator"`). Use `!=` or `NE` instead.

## Previously unverified, now confirmed (2026-09-17)

- **Plain (non-relative) date comparison** — `dateAdded > "2026-09-01"` works directly, confirmed alongside the relative `NOW() - N HOURS/DAYS` form already documented in `unified_object_queries.md`. Use whichever fits — plain dates for a fixed cutoff, relative for "the last N hours/days."
- **`hasAttribute()` on types other than `Description`, and exact-match filtering** — `hasAttribute(typeName = "Source" AND text = "Dataminr Pulse")` confirmed working: non-Description attribute types are filterable, and `=` (exact match) works alongside `CONTAINS`.
- **Comparison operators on indicator `confidence`/`rating`** — `confidence >= 50 AND rating <= 2` confirmed working, returns correctly-filtered results.
- **The combined score + topic IOC query** — `(hasGroup(hasTag(summary CONTAINS '<topic>') OR (summary CONTAINS '<topic>'))) AND threatAssessScore >= <N>` confirmed working as a single query (previously only each half was tested separately). Confirmed live: narrowed a topic search down to exactly the higher-confidence subset (2 hits, both confidence 70, vs. a larger set of low-confidence hits from the topic-only version) — this is the query to use whenever a user wants "solid IOCs for X," not the topic-only pattern alone. See `ioc_scoring_and_topic_queries.md`.
- **The `requirement` TQL field on `intelRequirements`** — confirmed correct: `requirement CONTAINS "SHINRA"` matches on `requirementText`. (Note: PIR checks are currently paused in active workflows per the decision in `association_traversal.md`/`SKILL.md` — this confirms the syntax for whenever that's revisited, not a reason to resume using it now.)

## Which date field to use for "what's new" — `dateAdded`/`lastModified` is the right default, not a limitation to work around

For "new/recent" queries, filter on `dateAdded` (or `lastModified` when you want to catch re-activity on an existing record, not just brand-new records) — **this is the correct default, not a stand-in for a "real" disclosure-date field.** Confirmed live: a "new critical Microsoft CVEs, past 7 days" sweep filtered on `dateAdded` surfaced CVE-2019-0708 (BlueKeep) alongside two genuinely new CVEs — at first glance this looks like a bug (a 7-year-old CVE showing up in a "new" query), but it's the platform correctly reporting that BlueKeep's record was recently (re-)added or touched in this instance, which is exactly the kind of thing a "what's new" query should surface: an old, well-known vulnerability suddenly becoming newly relevant again (renewed exploitation, a fresh feed starting to track it, new detections) is at least as important to know about as a brand-new CVE ID, arguably more so since it may mean active exploitation is happening right now.

`externalDateAdded`/`lastPublished` exist and reflect the *real-world* disclosure/publish date rather than platform activity — reach for these specifically when the user wants disclosure-date recency ("CVEs disclosed this week," not "CVEs active in the platform this week"). But don't default to them for general "what's new" asks, and don't treat an old CVE ID surfacing via `dateAdded` as noise — when it happens, say why it's there ("recently re-observed/updated in the platform," not "just disclosed") rather than filtering it out or flagging it as an error.

## Which text-search field varies by resource type — see `object_field_reference.md`

`summary` is correct for `groups`/`indicators`/`artifacts`, but **not universal** — `cases` use `name`, `tags` support both `name` (case-sensitive) and `summary` (case-insensitive). Check `object_field_reference.md`'s identifier-field table before querying a resource type you haven't used yet.

## `intelReqId` is valid only on Intelligence Requirement Results, not on groups/indicators directly

**Confirmed NOT valid** as a TQL field on `groups` (tested, failed with "not a known parameter"). `hasIntelRequirement(id = <PIR ID>)` **is** a valid, working nested query on both `groups` and `indicators` — but it only surfaces objects an analyst has manually associated to that PIR, which per the customer is rarely done. It is **not** a substitute for the platform's actual PIR match set (the Intelligence Requirement Results object, direct-API/dashboard-only) — see `association_traversal.md` for the corrected, full picture.

## General approach when a keyword is unknown

1. Run `tc_describe` for the resource type first — it gives you the *data model* fields (useful for knowing what exists) but **does not reliably give you the TQL keyword name**, as proven by `name`→`summary` and `groupType`→`typeName`.
2. If a guessed keyword fails, the error message names the exact rejected keyword (`Could not match subject 'X' to any known parameter`) — read it, don't retry the same guess.
3. When in doubt, start with the two universally-confirmed keywords (`summary` for text, `typeName` for group type) and layer in date/owner filtering via the dedicated `owner` parameter or client-side filtering on returned results rather than guessing more TQL syntax live in front of a customer.
4. Record any newly confirmed keyword back into this table so the skill improves over time.

## `fields=` accepts nested associations AND certain bundled scalar-data groups — not raw field names

`fields=tags,attributes,associatedGroups,associatedIndicators` (nested associations) is confirmed working throughout this skill. Separately, **some scores/metadata that don't appear in the default response are reachable via a named bundle, not the literal field name** — confirmed: `fields=threatassess` on indicators returns `threatAssessScore`, `calScore`, and related fields that are otherwise invisible even though they're valid TQL filter fields. Requesting the literal scalar name (`fields=threatassessscore`) fails with "Unrecognized fields parameter." When a field exists per `object_field_reference.md`/`tc_describe` but doesn't show up in a normal response, check whether it belongs to a named bundle before assuming it's unreachable.

## Combining filters

Confirmed working: `typeName EQ "Report" AND summary CONTAINS "APT28"` — standard `AND`/TQL boolean combination works as expected once individual keywords are correct.

## Common group `typeName` values seen in practice

`Report`, `Event`, `Incident`, `Adversary`, `Intrusion Set`, `Vulnerability`, `Malware`, `Document`, `Email`, `Campaign`, `Attack Pattern`, `Tactic` (see `group_types_taxonomy.md` for what each tends to contain and whether it's curated intel vs. raw feed noise). For CVE and threat-actor queries specifically, see `reference/unified_object_queries.md` first — `hasCommonVulnerability()`/`hasThreatActorProfile()` unified-object queries are usually a better starting point than a plain `typeName`/`summary` search.

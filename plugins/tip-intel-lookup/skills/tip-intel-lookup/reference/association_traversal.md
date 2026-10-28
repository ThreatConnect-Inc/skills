# Association Traversal & Context Assembly

Intel in a TIP is a graph: a `Report` links to `associatedGroups` (e.g. an `Adversary`, `Malware`, `Vulnerability`) and `associatedIndicators` (IOCs). Getting a *complete* answer means walking these edges — but doing it for every hit is expensive and will blow context on any non-trivial search (a single actor-name search returned 128 Report hits in testing).

## Two-pass strategy

**Pass 1 — triage, cheap:**
- Run the anchor search (see `tql_reference.md`) with `summary: true` on `tc_list`. This collapses associations/attributes/tags to `{"count": N}` instead of full arrays, so you get volume + titles + dates without the weight.
- Sort/skim by recency (`dateAdded`/`publishDate`) and, if visible, any severity/confidence signal, to pick the 3-10 most relevant items. Don't expand everything.
- Dedupe near-identical titles/topics before selecting (see `group_types_taxonomy.md`).

**Pass 2 — expand, only on selected anchors:**
- Re-fetch (`tc_get` or `tc_list` filtered to those specific IDs) with `fields=` set to whichever of `associatedGroups,associatedIndicators,associatedVictimAssets,tags,attributes,securityLabels` are relevant to the query.
- Nested association/attribute expansions are capped at **1000 rows** by the underlying API — fine for almost all cases, but if a hit is truly encyclopedic (e.g. a well-known actor with thousands of linked IOCs), say so rather than silently truncating without mention.
- One more hop is usually enough (Report → its associated Adversary/Malware/Vulnerability/IOCs). Don't recursively expand the associated objects' own associations unless the query specifically needs it (e.g. "what else is linked to this malware family") — that's how context blows up fast.

## Association by proxy — IOCs and victims often aren't linked to the entity you searched for

A very common gap: a Report/Event *about* an actor or CVE will have IOCs (and sometimes victim records) directly associated with **the Report**, not with the actor or CVE group object itself. Searching only the anchor entity's own `associatedIndicators`/`associatedVictimAssets` will come back empty even when the TIP clearly holds relevant IOCs and victims — they're just one hop further away, attached to the reporting that discusses the entity rather than to the entity record.

**Practical rule:** when a query needs "what IOCs/victims are associated with X," don't stop at X's own direct associations. Also:
1. Find the Reports/Events that discuss X (the same anchor search already done).
2. Pull *their* `associatedIndicators` and `associatedVictimAssets`.
3. Present these as associated-by-proxy with X — for intel purposes they're part of the same picture even though the platform's object graph doesn't draw a direct edge. Say so explicitly, e.g. "IOCs below were reported in connection with this campaign's write-ups, not directly tagged to the actor object itself."

This applies symmetrically to CVE lookups: a Vulnerability group frequently has no `associatedIndicators` at all (confirmed in testing — a same-day critical CVE's Vulnerability record had none), while its linked Reports may carry the actual observed indicators once attribution/exploitation detail matures.

## Surfacing victims, industries, and countries — usually inferred, not structured

Victim/org impact is high-value to users, but **don't expect it to show up as a populated `victims` resource or `associatedVictimAssets` field.** In practice, that dedicated object is often empty or unused even when a Report/Event clearly names who was affected. The same is true for targeted industry and targeted country: an instance *may* carry these as a dedicated tag or attribute, but very often the only place this information exists is free text.

**Practical rule — always do both:**
1. **Check the structured fields first** (`associatedVictimAssets`/`victims`, and any industry/country-shaped tags or attributes — e.g. the `NAICS: ...` tags seen in testing). If populated, use them — they're the most reliable signal when present.
2. **Read the free text regardless.** Scan the group's `summary`/`name` and its `attributes` (especially any `Description` attribute, which often carries the full syndicated article text) for named organizations, sectors, and countries/regions. This is genuinely a reading-comprehension task for the model, not a query — there is no reliable API filter to pull "victims mentioned in text" directly.
3. **State your confidence honestly.** A NAICS tag or a dedicated victim record is a firm signal; a name mentioned once in a paraphrased article is a weaker one. Say which kind of evidence you're presenting rather than treating both as equally certain — e.g. "tagged for the Financial Services sector (NAICS 52)" vs. "the report text names [Org] as affected, though this isn't tagged separately."
4. Apply the same by-proxy logic as IOCs: a victim/sector/country mentioned in a Report about an actor or CVE is relevant context for that actor/CVE even though the platform draws no direct edge for it.

## Pagination

`tc_list` returns a `next_token` for pagination and only includes the total `count` on the first page. If you need more than one page to answer a query, say how many results exist in total (from page 1's `count`) rather than presenting a partial list as if it were complete.

## PIR (Priority Intelligence Requirement) results

**STATUS: Paused in active workflows (2026-09-17).** Not currently invoked by any workflow in `SKILL.md` — see that file's "PIR / intel requirements briefing" section for why (confirmed low yield of the only MCP-reachable approximation, and a confirmed upstream `tc_resources` gap tracked separately — see tracker item G). Everything below remains accurate reference material, preserved for when the MCP server team adds the missing object type, or for the rare case a user explicitly insists on the approximation anyway.

**When a query touches many active PIRs (this instance has 39), don't exhaustively keyword-replicate every one of them, and don't arbitrarily spot-check just one or two either — short-list first, cheaply.** `intelRequirements` are typically a small enough list to fetch in full (a couple of pages at most) in one or two `tc_list` calls with no filter, which returns each PIR's `requirementText`, `description`, and full `keywordSections` (the actual keyword lists) in the response. Do this once, then **filter client-side** against the topic/industry/actor/CVE the user actually asked about — scan each PIR's own keywords for a match, not just its `requirementText` (a PIR like "SHINRA" or "PIR-1015" won't have the topic in its own name/description, only buried in its `keywordSections`). Only run the full literal-keyword-replication TQL query (scoped to whatever timeframe the user asked for) against the PIRs that survive this short-list step — not all 39, and not an arbitrary sample. This turns an unscalable "check every PIR" problem into a cheap pre-filter plus a small number of targeted follow-up queries.

Each `intelRequirements` record includes a `resultsLink` (e.g. `.../api/v3/intelRequirements/results?tql=intelReqId=<id>`) and its own `id`. **Correction to an earlier version of this skill:** a nested query, `hasIntelRequirement(id = <PIR ID>)` on `groups`/`indicators`, does work syntactically over MCP — but it is **low-yield in practice** and should not be treated as the primary way to get PIR results.

**Why it's low-yield:** the platform's automatic PIR matching does not, by default, create an association between the matched object and the PIR. An object only shows up under `hasIntelRequirement()` if someone has taken the *separate, manual* action of explicitly associating it to the PIR — and per the customer, most users don't do this. So `hasIntelRequirement()` mostly reflects analyst curation, not the platform's actual match set. Treat a result from it as "someone specifically flagged this against this PIR" (a real, if narrow, signal), not as "these are the PIR's matches."

**The real PIR matches — the ones a "what's new from my intel requirements" briefing actually needs — live on the separate Intelligence Requirement Results object,** which is v3-API/dashboard-only and not reachable via any MCP `tc_*` tool. **Re-confirmed more thoroughly:** tried the resource type directly (`intelRequirementResults` and naming variants), and a `fields=results` expansion on `intelRequirements` itself — every approach fails (not in `tc_resources`, rejected as an unknown resource type, rejected as an unrecognized fields parameter). There is currently no way to reach this object through the MCP tool surface, however the query is constructed.

**Status: known upstream gap, tracked for the MCP server team — not something to keep working around indefinitely.** The customer has confirmed this is a genuine `tc_resources` omission (the MCP server itself doesn't expose this object type, not a query-construction problem on this skill's side) and is raising it with the team that builds the MCP server. Once `intelRequirementResults` (or equivalent) is added to `tc_resources`, this section should be revisited — the fallback logic below can likely be retired in favor of querying that resource type directly.

**If direct API access is available in the meantime** (see `direct_api_fallback.md`): hit `resultsLink` directly — this is the correct, complete path and should be preferred whenever it's available. **A confirmed-correct query shape for bulk multi-PIR checks, for whenever this object becomes reachable (via MCP once added, or via direct API today):** after short-listing the relevant PIRs (as above), query the results object directly across all of them at once rather than one PIR at a time:
```
hasIntelRequirement(uniqueId = "PIR-1" OR uniqueId = "PIR-2" OR uniqueId = "PIR-3") AND lastMatchedDate > "NOW() - 24 HOURS" AND intelType IN ("Event","Report")
```
This is the right pattern for the Intelligence Requirement Results object specifically (its own fields, per `object_field_reference.md`, include `intelReqId`/`uniqueId`, `lastMatchedDate`, `intelType`, `isFalsePositive`, `score`) — it does **not** work against `groups`/`indicators` (confirmed: `lastMatchedDate` is rejected as an unknown parameter on both). Preserve this pattern — it directly solves the "short-list PIRs, then bulk-check them" problem in a single call instead of one PIR at a time, and is exactly what to try first once this object type is added to `tc_resources`.

**If MCP-only:** replicate the PIR's logic manually — this is the primary approach in this scenario, not a fallback:
1. `tc_list` on `intelRequirements` to get the PIR object, including its `keywordSections` — each section has a `compareValue` (`includes`/`excludes`) and a `keywords` array.
2. Build the literal-keyword version first: `summary CONTAINS "<keyword>"`, OR'd together across a section's `includes` keywords, and excluded (`AND NOT ...`) for `excludes` keywords. **This is the more faithful replication of what the PIR's own keyword definition actually means** — the PIR's `keywordSections` are a text/keyword-matching rule, so a literal text-match query is answering the same question the PIR itself asks, alias-by-alias.
3. **`hasThreatActorProfile()`/`hasCommonVulnerability()` answers a different question, not a better version of the same one** — confirmed by direct comparison on PIR-1015 (APT28/CHOPSTICK, whose `keywordSections` already enumerate 15 aliases): the literal-keyword query returned 322 hits, all genuinely naming APT28/its aliases in the title or text; swapping the `apt28` keyword for `hasGroup(hasThreatActorProfile(summary="APT28"))` grew that to 873, adding every Report/Event *structurally associated* with the APT28 profile in the graph — including ones that don't mention APT28 anywhere in their own text (an AV-certification article, an unrelated lawsuit story), because they carry the tag/association for some other reason (e.g. bulk automated enrichment tagging many TTPs/actors onto one general article). Neither result set is "wrong" — they answer genuinely different questions ("mentions this by name" vs. "linked to this profile in the graph") — but for *replicating a PIR's keyword definition specifically*, the literal-keyword version is the closer match, since the PIR itself is defined as keyword matching, not graph association.
4. Treat the unified-object query as a **separate, additional check**, not a substitution: run it alongside the literal-keyword version and present it labeled as its own thing (e.g. "Also structurally linked to the APT28 profile in the platform, though not necessarily naming APT28 in the text:") rather than merging both into one undifferentiated result set with `OR`.
5. This is still an approximation of the platform's own PIR matching, not a guarantee of identical results. Tell the user this is an approximation, and recommend direct API access for exact PIR results if precision matters.
6. Optionally, also check `hasIntelRequirement(id=<PIR ID>)` as a supplementary signal — anything it returns has been deliberately curated by an analyst against this PIR, which is worth surfacing (with that context) alongside the keyword-approximation results, just not relied on as the complete picture.

## Two genuinely different questions, not one query done two ways

This distinction matters beyond PIR replication, for any entity lookup:
- **`summary CONTAINS "<name/alias>"`** answers "does this appear in the object's own title/text." Narrower, but every hit is self-evidently on-topic without needing to check further.
- **`hasGroup(hasThreatActorProfile(...))` / `hasGroup(hasCommonVulnerability(...))` / `hasTag(...)`** answers "is this object structurally associated with/tagged as X in the platform's graph." Broader — correctly catches real associations a text search would miss (a report that discusses an actor's activity without naming the actor in its own title) — but "associated" doesn't mean "primarily about." A tag-association match in particular doesn't imply centrality: objects are frequently multi-tagged (a report can carry a dozen TTP tags), so `hasTag(techniqueId = "T1566")` finding a hit means that tag is *applied*, not that phishing is what the report is about.

**Practical rule:** pick based on what the user actually asked. "What mentions APT28" → text search. "What's linked to the APT28 profile" → graph query. When it's ambiguous which the user wants, or both are useful, run both and label them separately rather than combining into one list — combining hides the fact that they're different kinds of evidence with different confidence levels.

## Attribute/tag names vary per instance

Field *types* (e.g. "GroupAttribute", "Tag") are consistent, but the actual attribute type names and tag taxonomies (e.g. what a "targeted industry" or "targeted country" attribute is called) are configured per instance. Run `tc_describe` and/or list a few known-good records' `attributes`/`tags` expansions early in an engagement to learn the instance's actual vocabulary before assuming a specific attribute name — then note it in the customer context so it doesn't need rediscovering every session.

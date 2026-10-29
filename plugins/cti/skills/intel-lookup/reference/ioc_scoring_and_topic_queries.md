# IOC Prioritization & Topic-Based Discovery

Two confirmed, complementary approaches for finding IOCs that actually matter, rather than everything that's ever been ingested.

## Score-based prioritization

Confirmed working, **no type filter — this is the default** unless the user names a specific IOC type (IPs, domains, hashes, URLs):
```
threatAssessScore >= 700 AND NOT (calScore <= 100) AND falsePositiveCount = 0 AND dateAdded > "NOW() - 1 DAY" AND (indicatorActive = false OR indicatorActive = true)
```
Only add `typeName = "Address"` (or `Host`/`File`/`URL`) when the user's own wording asks for that specific type ("nastiest new IPs," "bad file hashes"). A generic ask ("nastiest IOCs," "what should I flag") must sweep every indicator type — scoping to one type by default silently drops other types from the answer. **Confirmed live** (7-day window, otherwise identical conditions): `typeName = "Address"` alone returned 7 hits; removing the type filter returned 267 hits total, breaking down as 243 File-type hashes, 17 URLs, and the original 7 Addresses — the type-scoped version was silently excluding the large majority of what was actually there.

**Also always include `(indicatorActive = false OR indicatorActive = true)`** — same reasoning as the batch IOC lookup workflow (`ioc_batch_lookup.md`): without it, the MCP server's default `indicatorActive=true` injection silently excludes any deactivated/false-positive-flagged indicator, even one TC has already scored and knows about. A "nastiest IOCs" sweep that misses known bad-but-deactivated indicators isn't complete.

- `threatAssessScore` (0–1000ish scale) is the platform's own composite confidence/severity score — `>= 700` is a reasonable "high" bar, adjust with the customer's own risk tolerance if they've stated one (see `customer_context_template.md`).
- `NOT (calScore <= 100)` excludes IOCs CAL hasn't meaningfully scored yet or scored very low — this is specifically a **false-positive/unscored filter**, not a severity filter; don't confuse it with "must be high severity per CAL."
- `falsePositiveCount = 0` excludes anything the community/platform has already flagged as a false positive.
- **Combine with recency** (`dateAdded` or `lastModified` relative filters) — without it, this can return a large historical backlog rather than "what's new."
- **Watch for a large batch sharing an identical score profile from one feed.** Confirmed live: within the 267-hit set above, roughly 240 shared the exact same `threatAssessScore`/`calScore`/`confidence` values, all from `abuse.ch ThreatFox`, added within a few minutes of each other. This is very likely a single bulk-ingest batch, not independently-assessed IOCs — when presenting results, note "N of M hits share an identical score profile from one feed" as a signal, rather than listing them as if each were separately evaluated.

**This is a precision tool for volume, not relevance to a specific topic.** A high-scoring IP with no topic connection to what the user actually asked about isn't a good answer to "show me IOCs for DragonForce" — for that, use the topic-based pattern below, and combine both when the user wants "high-confidence IOCs specifically tied to X."

## Topic-based IOC discovery (association by proxy, formalized as TQL)

Confirmed working:
```
(hasGroup(hasTag(summary CONTAINS 'Dragonforce') OR (summary CONTAINS 'Dragonforce'))) AND lastModified > "NOW() - 14 DAYS" AND (indicatorActive = false OR indicatorActive = true)
```
This is the TQL-native version of the "association by proxy" pattern in `association_traversal.md`: it finds indicators associated to *any Group* that either (a) is tagged with the topic, or (b) mentions the topic in its own summary — covering both a curated tag and a plain-text match in one query, without needing to first find the Reports/Events manually and then separately query their indicators. **Includes the `indicatorActive` override for the same reason as the score-based pattern above** — without it, a deactivated/false-positive IOC tied to this topic would be silently excluded rather than surfaced as a known false positive.

**Caveat confirmed in testing:** this pattern is topic-relevant but not score-filtered — results in testing were correctly on-topic (DragonForce-adjacent domains) but had low/unscored confidence and rating values. **For "give me solid IOCs for X," combine both patterns** — wrap the topic condition and the score condition together in one query rather than presenting an unscored topic-match list as if it were high-confidence:
```
(hasGroup(hasTag(summary CONTAINS 'Dragonforce') OR (summary CONTAINS 'Dragonforce'))) AND lastModified > "NOW() - 14 DAYS" AND threatAssessScore >= 700 AND (indicatorActive = false OR indicatorActive = true)
```
**Confirmed working combined** (2026-09-17): tested `(hasGroup(hasTag(summary CONTAINS 'Dragonforce') OR (summary CONTAINS 'Dragonforce'))) AND threatAssessScore >= 700` live — returned exactly 2 hits, both confidence 70, a meaningfully tighter and higher-quality result than the topic-only version (which returned unscored/low-confidence hits in earlier testing). Use this combined form whenever the user wants "solid IOCs for X," not the topic-only pattern alone.

**For a MITRE-normalized actor or a CVE specifically**, prefer `hasThreatActorProfile()`/`hasCommonVulnerability()` inside the `hasGroup()` wrapper over a plain `summary CONTAINS` topic string when the entity resolves to a primary name (see `unified_object_queries.md`) — more precise, correctly picks up aliases, avoids the plain-text version's risk of matching unrelated mentions.

## Getting the actual score values — use `fields=threatassess`

The score-based query above filters correctly on `threatAssessScore`/`calScore`, but **those numbers don't come back in the response by default** — confirmed via both `tc_list` and `tc_get`, even though they're valid TQL fields. **Add `fields=threatassess` to the request** (a bundled field, not the literal scalar field names like `threatassessscore`, which fails) to get them back. Confirmed working — returns:
- `threatAssessRating`, `threatAssessConfidence`
- `threatAssessScore` (the number you filtered on)
- `threatAssessScoreObserved`, `threatAssessScoreFalsePositive`
- `calScore`, `calLastChecked`

Without this, you can filter on high scores but can't show the user the actual number — don't present a result set as "high severity" without pulling the real figures if the user might want them (e.g. for a report or CSV export).

## IOCs as a secondary complement to group/topic intel, not the default lead

For entity/topic lookups (an actor, a CVE, a ransomware group, "what's happening with X"), **default to the group/topic-based answer — don't lead with an IOC-scoring pass unless the user specifically asked about IOCs.** That said, a short "associated high-severity IOCs" addition alongside the main answer is a genuine value-add: it gives the user something immediately actionable to check against their own environment, on top of the narrative intel. Run the topic-based IOC pattern (combined with the score filter above) as a follow-up after the group-based answer, and present it as a labeled secondary section — not merged into the main narrative, and not run at all if it doesn't turn up anything worth mentioning. The user's own phrasing decides how much weight this gets: "what's new for DragonForce" → group/topic answer with a short IOC addendum if relevant; "show me DragonForce IOCs" → IOCs are the actual ask, lead with them.

## Which one to reach for

| User's ask | Pattern |
|---|---|
| "What are the nastiest new IOCs overall" | Score-based, no topic filter |
| "IOCs for [actor/CVE/malware/campaign]" | Topic-based (or unified-object-wrapped if it resolves to a primary name) |
| "Solid/confirmed IOCs for [topic]" | Both, combined |
| Daily triage / "what should I prioritize" | Score-based as one input signal alongside whatever else the customer's stated priority signals call for (PIR matches, tags, recency — see `customer_context_template.md`) |

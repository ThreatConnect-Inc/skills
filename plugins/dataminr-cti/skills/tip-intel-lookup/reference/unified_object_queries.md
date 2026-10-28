# Unified Object Queries — hasCommonVulnerability(), hasThreatActorProfile(), hasCommonGroup()

CVEs and threat actors have a special data model in this platform: the TIP auto-consolidates multiple feeds' separate records of the *same* CVE or actor (matched by alias) into one **unified/"common" object**. This matters a lot for intel quality — it's the difference between manually reconciling 4 different owners' Vulnerability records yourself (as done in early testing of this skill) and letting the platform hand you the reconciled view directly.

**Always pull `fields=common` when querying `typeName IN ("Vulnerability", "Adversary", "Intrusion Set", "Threat Group")`.** This attaches a `commonGroup` object to each result containing the platform's own normalized data — confirmed live: for a same-day Cisco ISE CVE, `commonGroup` already carried the *official Cisco PSIRT* CVSS score/vector and KEV properties, independent of and more authoritative than any single feed's (VulnCheck's, Dataminr Pulse's) self-reported numbers. Feed-specific attributes (EPSS score, PoC links, exploit-maturity flags) still only live on the individual owner records, so still check those too — `commonGroup` doesn't replace per-feed enrichment, it adds the authoritative baseline underneath it.

## The two nested-query functions

- **`hasCommonVulnerability(...)`** — matches Vulnerability groups belonging to a unified Vulnerability object. Use this to find *the* CVE regardless of which feed's copy you land on.
- **`hasThreatActorProfile(...)`** — matches Adversary/Intrusion Set/Threat Group records belonging to a unified Threat Actor Profile. Use this to find *the* actor regardless of alias (SEDNIT / FANCY BEAR / APT28 all resolve to the same profile — confirmed live).
- **`hasCommonGroup(...)`** — the general form covering both unified Vulnerability groups AND unified Threat Actor Profiles; `hasCommonVulnerability()` is the Vulnerability-only shorthand. Reach for the specific one when you know which kind you want.
- **`hasGroup(...)`** — wraps any of the above to reach from a *different* object (typically `Report`/`Event`) to its associated Groups. This is how you find "reports about X" rather than "the X object itself."

## Confirmed syntax patterns

Find the unified actor/CVE object itself, with normalized data:
```
typeName IN ("Adversary","Intrusion Set") AND hasThreatActorProfile(summary = "APT28")
```
(fetch with `fields=common` to get the normalized profile attached to each per-feed record)

**Resolving the entity object is only the first half of an entity lookup — always chain a second query for recent associated intel.** Confirmed live: stopping at the object above tells you the entity exists and its normalized profile, but not what's actually happening with it. Run both of these together for a MITRE-tracked actor, not one instead of the other:
```
typeName IN ("Report","Event") AND hasGroup(hasThreatActorProfile(summary = "APT28")) AND dateAdded > "NOW() - 7 DAYS"
typeName IN ("Report","Event") AND (summary CONTAINS "apt28" OR summary CONTAINS "sofacy" OR summary CONTAINS "sednit" OR summary CONTAINS "fancy bear") AND dateAdded > "NOW() - 7 DAYS"
```
They answer different questions (see "Two genuinely different questions" below) — run both, treat the association hit as the stronger signal when the same item shows up in both, and present anything found only via the literal-text query as a secondary, clearly-labeled list. If both come back empty, extend the lookback (e.g. to 30 days) before concluding there's nothing new — don't stop at a single narrow window. For a non-MITRE actor with no profile to query, skip the first line but still run the second (literal name/alias) — the point is always to surface recent activity, not just confirm the entity exists.

Find Reports/Events about a named actor (by MITRE primary name):
```
typeName IN ("Report","Event") AND hasGroup(hasThreatActorProfile(summary = "APT28"))
```
Add a recency window:
```
... AND dateAdded > "NOW() - 24 HOURS"
```
(confirmed: `NOW() - <n> HOURS`/`DAYS` relative date syntax works)

Find Reports/Events about a named CVE:
```
typeName IN ("Report","Event") AND hasGroup(hasCommonVulnerability(summary = "CVE-2026-76460"))
```

Find Reports/Events about a malware family (no unified-object equivalent for malware — plain group-type filter):
```
typeName IN ("Report","Event") AND hasGroup(typeName = "Malware")
```
**If a malware-family name search comes back empty, don't conclude the malware isn't in the instance yet.** Confirmed live: `typeName EQ "Malware" AND summary CONTAINS "Atomic macOS Stealer"` returned zero, but the record exists under the abbreviation `AMOS` — "Atomic macOS Stealer" exists only as a Tag, not as the Group's own name. Malware has no alias-resolution mechanism at all (no unified object, unlike CVEs/actors — see below), so a correct, commonly-used name can miss the record entirely.

**Check the tag alias on both `groups` and `indicators` — don't assume it's on only one.** In this instance, `hasTag(name CONTAINS "Atomic macOS Stealer")` returns zero on `groups` but 815 hits on `indicators` (confirmed by expanding the Malware Group's own `tags`: only `AMOS`, never the full name, in this dataset). That's a property of *this* data, not a platform rule — a different feed/instance could just as easily tag the alias directly on the Malware Group instead. So when a name search on `typeName = "Malware"` comes back empty, retry the alias via `hasTag(name CONTAINS "<name>")` on **both** `groups` and `indicators` rather than assuming which one holds it. If you need to find the Group's real stored name from a full name the user gave and only the indicator-side tag resolves, use a co-occurring-tag bridge: pull one matching indicator's full tag list — confirmed live, one had both `AMOS` and `Atomic macOS Stealer` together — and use whichever tag also matches a `typeName = "Malware"` Group's own name.

Find new CVEs tied to a specific vendor:
```
hasCommonVulnerability(hasAffectedProduct(vendor IN ("Cisco"))) AND dateAdded > "NOW() - 24 HOURS"
```
Same, but for Reports/Events discussing them:
```
typeName IN ("Report","Event") AND hasGroup(hasCommonVulnerability(hasAffectedProduct(vendor IN ("Cisco"))) AND dateAdded > "NOW() - 24 HOURS")
```

CVSS range filtering (combinable across versions):
```
hasCommonVulnerability(cvss_score_v4 = 10 AND cvss_score_v3_1 > 9.5)
```

Free-text scan across summary, tags, and description for a keyword (e.g. "npm") in the last 24-48h — powerful but expensive, don't run over wide date ranges:
```
typeName IN ("Report","Event","Vulnerability") AND (summary CONTAINS "npm" OR hasTag(name CONTAINS "npm") OR hasAttribute(typeName = "Description" AND text CONTAINS "npm")) AND dateAdded > "NOW() - 24 HOURS"
```

## Critical limitation: alias resolution only works for the MITRE primary name

`hasThreatActorProfile(summary = "APT28")` works because APT28 is the actor's MITRE ATT&CK primary name. **`hasThreatActorProfile(summary = "FANCY BEAR")` does NOT work** — the function only matches on the MITRE primary name, not alternate aliases, even though the unified profile itself *contains* those aliases as separate underlying group records.

**Practical rule:** if you don't already know the MITRE primary name for an actor the user named by an alias, don't guess — fall back to a plain group search (`typeName IN ("Adversary","Intrusion Set") AND summary CONTAINS "<alias>"`) to find a record, then read its `commonGroup.name` (if present) to get the real primary name for any follow-up `hasThreatActorProfile()` queries.

## Critical limitation: non-MITRE actors have no Threat Actor Profile at all

Many active groups — especially ransomware crews — aren't in the MITRE ATT&CK framework and therefore have **no unified Threat Actor Profile**, so `hasThreatActorProfile()` will never match them, no matter what name you try. (Observed live: "Royal Ransomware Group" exists only as a plain `Adversary` group record with no `commonGroup`, unlike APT28's fully-normalized profile.)

**Practical rule:** for a wide/generic actor search where you're not sure if the group is MITRE-tracked, search broadly across `typeName IN ("Adversary","Intrusion Set","Threat Group")` with `summary CONTAINS "<name>"` rather than assuming `hasThreatActorProfile()` will catch it. Only rely on `hasThreatActorProfile()` once you've confirmed the actor has a MITRE ID (check for a `commonGroup.mitreId` on a known record) — **and don't substitute a plausible-looking shortcut for that check.** Confirmed live: a plain-search result for a non-MITRE-tracked actor ("TeamPCP") was itself owned by a feed literally named "MITRE ATT&CK," which looks like it should imply profile linkage but doesn't — `hasThreatActorProfile()` still correctly returned empty for it. Owner name (custom feeds can be named anything, and even a genuinely MITRE-sourced feed can carry records that were never promoted to a full Threat Actor Profile) is not a valid substitute for checking `commonGroup.mitreId` directly.

## Same fallback logic applies to very fresh CVEs

A CVE that has just been assigned may not have a unified Vulnerability object yet if the platform hasn't had time to normalize it. **Fallback:** if `hasCommonVulnerability(summary = "<CVE-ID>")` returns nothing, drop back to the plain group query documented in `tql_reference.md`: `typeName EQ "Vulnerability" AND summary EQ "<CVE-ID>"` (exact match, not CONTAINS — see that file for why).

## Two different questions: structurally associated vs. explicitly named

**Confirmed live:** `typeName IN ("Report","Event") AND hasGroup(hasThreatActorProfile(summary = "APT28"))` returned 873 hits, including a "Bitdefender Achieves AV-Comparatives Certification" article. Checked its own associations: it's genuinely, structurally linked to the APT28 Intrusion Set group in the graph — alongside APT29, KIMSUKY, FIN7, WANNACRY, BLACK BASTA, and a long list of generic ATT&CK Tactics. **This is not a query error or noise** — the query correctly answers "what's associated with the APT28 profile," and this article really is associated with it (evidently via a bulk automated-enrichment pipeline attaching a broad, boilerplate set of actor/TTP tags to general cybersecurity-adjacent articles). It's just a different, broader question than "what's substantively about APT28."

By direct comparison, `typeName IN ("Report","Event") AND (summary CONTAINS "apt28" OR summary CONTAINS "sofacy" OR summary CONTAINS "sednit" OR ...)` — text-matching the same actor's known aliases — returned 322 hits, all of which named APT28 or an alias directly in their own title/text.

**Neither is "the right one."** They're complementary:
- `hasGroup(hasThreatActorProfile(...))` / `hasGroup(hasCommonVulnerability(...))`: broader recall, catches real associations a text search misses (a report discussing an actor's tooling without naming the actor in its own title) — but a hit doesn't mean the object is *primarily about* that entity, only that it's linked to it somewhere in the graph. Don't present a hit from this pattern as "intel about X" without checking the object's own title/text (or its Description attribute) confirms it's substantively on-topic, not just present in a long boilerplate association list.
- `summary CONTAINS "<name/alias>"`: narrower, but every hit is self-evidently on-topic without further checking, since the name appears in the object's own text.

**Practical rule:** match the query to what the user actually wants. "What's linked to APT28" → the graph query. "What names APT28" → text search. When it's unclear which the user means, or both would help, run both and present them **labeled separately** ("directly associated with the APT28 profile" vs. "explicitly named in the text") rather than merging them with `OR` into one undifferentiated list — merging hides that they're different kinds of evidence with different confidence levels. See `association_traversal.md`'s PIR section for a worked example of this same tradeoff.

**This same breadth applies to `hasTag()` and any other association-style nested query, not just actor/CVE profiles.** Confirmed live: `hasTag(techniqueId = "T1566")` (the Phishing TTP tag) over 14 days returned 449 hits, sampled titles including "Cyber Essentials Has Record Year," "Cyble, UAE Cyber Security Council Unite Against Rising Cyber Threats," and "Telegram Desktop flaw leaves old chat exports exposed" — genuinely tagged T1566, but not substantively about phishing. **A tag-association match means the tag is applied, not that the tagged concept is the object's central topic** — objects are routinely multi-tagged (a single report can carry a dozen TTP tags), so treat any `hasTag()`/`hasAllTags()` hit the same way: a candidate to skim, not a confirmed on-topic result, especially at wide date ranges or against heavily-enriched owners.

## General rule: try common formatting variants, not just the exact string typed

Users type entity names inconsistently — with/without internal spacing (`FIN7` vs `FIN 7`), different casing, or abbreviated vs full names. `CONTAINS` already handles some of this for free since it's a substring match (`summary CONTAINS "LAPSUS"` correctly matches text containing `"LAPSUS$"` — no need to strip the trailing symbol, confirmed live), but it does **not** bridge a spacing/punctuation difference: `summary CONTAINS "FIN7"` will not match text that actually reads `"FIN 7"`, and vice versa, because they're different substrings. Exact-match fields (`EQ`, and the primary-name parameter inside `hasThreatActorProfile()`/`hasCommonVulnerability()`) are even less forgiving — they need the precise stored string. If a first search comes back empty, retry with a spacing/punctuation variant before concluding the entity isn't in the platform — the same way a malware alias or actor alias gap (see above) would otherwise cause a false "not found."

## Most feeds use "Intrusion Set," not just "Adversary"

When searching broadly for actor-type groups (not via `hasThreatActorProfile()`), include both: `typeName IN ("Adversary","Intrusion Set","Threat Group")`. Most curated feeds populate `Intrusion Set` for MITRE-aligned actors; `Adversary` shows up too (e.g. VulnCheck's "Fancy Bear" record), and some non-MITRE actors only exist as `Adversary`.

## Reference tables

Full parameter lists for `hasCommonVulnerability()`/`hasCommonGroup()`, `hasAffectedProduct()`, and `hasThreatActorProfile()` are in the project's own reference documents (CVE TQL parameters, Threat Actor TQL parameters) — consult those directly for the complete field list (CVSS fields across v2/v3/v3.1/v4, KEV-specific fields like `dueDate`/`requiredAction`/`knownRansomwareCampaignUse`, and `hasAffectedProduct()`'s CPE-shaped fields like `vendor`/`product`/`version`/`targetSw`/`targetHw`). If similar parameter references for other object types (groups, indicators, cases) become available, add them here the same way.

# Group Type Taxonomy

`groups` is the workhorse resource type for curated intel, but it's also where raw, high-volume wire feed lands in many instances. Filtering by `typeName` (see `tql_reference.md`) before searching text is usually the difference between a useful answer and a firehose of noise.

**This taxonomy is a starting guide, not a guarantee** — instances vary, and custom group types can exist. When unsure, run `tc_resources`/`tc_describe` against the live instance rather than assuming this list is exhaustive.

## High signal — curated/analyst-relevant intel

| Type | Typically contains | Use for |
|---|---|---|
| `Report` | Analyst or vendor write-ups, CTI feed reports (e.g. from a CAL/automated threat library), often the richest source with full context and links to actors/malware/CVEs | Entity lookups, "latest intel on X" |
| `Adversary` | Named threat actor / intrusion set profiles | "Tell me about [actor]" anchor |
| `Malware` | Malware family profiles | Campaign/actor context |
| `Vulnerability` | CVE-specific records | CVE lookups — check both here AND `Report` typeName, a CVE is often *discussed in* a Report even if it also has its own Vulnerability record. **Different owners frequently hold separate Vulnerability records for the same CVE with different attribute sets** (observed: a CAL Automated Threat Library record with just the CVE ID and linked Reports, alongside a VulnCheck Intelligence record carrying the actual CVSS score/vector, affected CPEs/products, and exploitation/KEV metadata). Check all owners' records for a given CVE, not just the first hit — the structured fields you need most (CVSS, CPEs, exploitation status) may sit on a different owner's record than the narrative. Always surface CVSS score/vector, affected products/CPEs, and exploitation status when present — these drive urgency and are easy to bury in prose. |
| `Campaign` | Named multi-incident campaigns | Broader activity clusters |
| `Incident` | Confirmed incidents (internal or third-party) | Impact/incident-driven queries |

## Lower signal / high volume — filter carefully, dedupe aggressively

| Type | Typically contains | Caution |
|---|---|---|
| `Event` | Raw wire/news items (e.g. Dataminr Pulse alerts) — outages, breaking news, low-context single-line items | Very high volume, often not curated threat intel at all (observed: general news, service outages, police incidents mixed in with genuine security events). Don't treat an `Event` hit as equivalent in weight to a `Report` hit. |
| `Document` | Uploaded files, may or may not be malware-flagged | Check the `malware` boolean field before treating as a threat artifact |
| `Email` | Ingested email content | Usually phishing-sample specific |

## Near-duplicate awareness

Multi-language/multi-source feeds (e.g. CAL Automated Threat Library) frequently create multiple `Report` entries for the same underlying story — observed in testing as near-identical titles in different languages (English/Ukrainian/Thai versions of the same Google Pixel zero-day, for example). When assembling an answer:
- Group by underlying topic/date/CVE-ID rather than by individual group ID.
- Don't present duplicate translated versions as separate pieces of intel — mention once, note "reported across N sources/languages" if that itself is a useful signal (e.g. broad international pickup of a story).

## Owner/source scoping

Large instances mix multiple `owner`s — e.g. an org's own analyst-authored content, a raw ingestion feed owner (like "Dataminr"), and an automated enrichment owner (like "CAL Automated Threat Library"). Use the `owner` parameter on `tc_list` to scope a query when the customer context indicates they only care about their own curated org content vs. the full raw+curated mix. If unclear, ask, or default to searching across all owners and noting the source/owner in the summary so the user can judge signal quality themselves.

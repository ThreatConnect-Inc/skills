# Citing & Linking TIP Data

Every object returned by `tc_list`/`tc_get` carries a `webLink` field (e.g. `https://<instance>/#/details/groups/<id>` or `.../details/indicators/<id>`) — the direct in-platform URL to that record. Use this to give answers provenance and let the user deep-dive, but do it selectively — this is about giving the user exactly what they need, not padding every answer with links.

**This applies to every workflow's output, not just single-entity lookups.** Daily-triage rankings, industry/country roundups, PIR briefings, case-triage lists — every generated response that makes a specific claim about a specific TIP object should link it the same way an entity lookup does. It's easy to drift toward citing carefully on a "tell me about CVE-X" answer and then dropping the discipline on a multi-item roundup where each individual item gets less attention — don't. The same "load-bearing items only, not everything" rule below still applies; the point is consistency of habit, not exhaustiveness.

## Link the unified object, not every per-feed copy

For CVEs and MITRE-normalized actors, multiple feed-specific records resolve to one `commonGroup` (see `unified_object_queries.md`). **Link to the `commonGroup`'s own `webLink`/id**, not each individual owner's copy — the whole point of the unified object is that the user shouldn't have to sort through 4 near-identical links for the same CVE. Only surface a specific feed's own link when you're citing something unique to that feed (e.g. "VulnCheck's exploitation-tracking record specifically" → link that one).

## Be selective — cite the load-bearing items, not everything

If a search returned 43 hits, don't link all 43. Link:
- The 1–3 items an answer's key claims actually rest on (the source of a specific fact, quote, or number)
- Anything unusual, high-impact, or likely to prompt a follow-up ("the newest report, which changed the affected version range")
- The unified/anchor object itself, once, as the natural "start here" link

Everything else stays as a plain count/summary ("43 Reports/Events reference this, mostly syndicated coverage of the same story") with no individual links. A wall of links is as unhelpful as no links — it just relocates the triage work onto the user instead of doing it for them.

## For genuinely broad result sets, offer the TQL — but only as an offered option, not by default

When a result set is large enough that the user might reasonably want to review the *whole* thing themselves in-platform (not just the curated highlights you're presenting), you can offer the underlying TQL query as something they can paste into their own Advanced Search/Browse screen. **This should be an offer, not an automatic addition to every answer** — e.g. "want the TQL query so you can browse all 43 in-platform?" Don't include it unprompted for small or already-fully-summarized result sets; only surface it when the volume genuinely exceeds what's useful to summarize inline, and let the user opt in.

## Practical shape of an answer

- Lead with the synthesis (as the core retrieval pattern already directs) — links support the claims, they don't replace the synthesis.
- Inline-link entity names/report titles the first time they're mentioned, rather than a trailing "sources" list that disconnects the link from the claim it supports.
- If direct API is in use instead of MCP, the same `webLink` field is present in the JSON response — no difference in approach.

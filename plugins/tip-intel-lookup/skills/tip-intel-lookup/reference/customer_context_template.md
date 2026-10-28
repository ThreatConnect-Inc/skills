# Customer Context Template

This is a **template**, not live data. When this skill is used for a real customer/engagement for the first time, create an actual `customer_context.md` (in the project or conversation working notes — wherever persists for this engagement) using this shape, fill it in conversationally as needed, and reuse it across sessions rather than re-asking every time.

```markdown
# Customer Context: <customer/org name>

## Profile
- Industry: <e.g. Financial Services>
- Country/region: <e.g. United States, or multi-region list>
- TIP instance base URL: <if using direct API path>
- Default owner(s)/source(s) to scope queries to: <e.g. "ACME" org content only, or "all owners">

## Watchlist
- Named threat actors of specific interest: <list>
- Named malware families of specific interest: <list>
- Specific CVEs/tags currently being tracked: <list>

## Daily triage priority signals
How this customer wants "what should I prioritize" ranked — capture their actual stated preference, don't assume a default:
- <e.g. "PIR matches first, then anything tagged critical/high confidence, then recency">
- <e.g. "Pure recency — I just want to see everything from the last 24h in date order">

## Instance-specific vocabulary (learned, not assumed)
Attribute/tag names actually used in this instance for common concepts (varies per install — see association_traversal.md):
- "Targeted industry" attribute/tag name: <once learned>
- "Targeted country" attribute/tag name: <once learned>
- Other notable custom attribute types: <as discovered>

## Report/output preferences
- Preferred format for generated reports: <inline chat / markdown doc / house template — ask, don't assume>
- Standing structure, if any: <captured once confirmed>

## Session notes
- Last "what's changed since I last checked" timestamp per topic: <topic: date, as tracked>
```

## Usage rule

Ask for missing fields **only when a query actually needs them** — don't front-load a big intake questionnaire before the user has asked anything. E.g. a plain "tell me about CVE-2026-58704" needs none of this; "is this impacting my industry" needs the Profile section; daily triage needs the priority signals section. Fill in lazily, confirm with the user before saving, and reuse afterward.

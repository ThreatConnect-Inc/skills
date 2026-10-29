# IOC Lookup — Single, Pasted List, or CSV Upload

Handles "does TC know about this IOC" for one IOC, a handful pasted into chat, or a bulk list from a file — the most common real-world ask.

## Input handling

- **Single IOC or a short pasted list (up to 15):** work with what's in the chat directly, no upload needed.
- **More than 15 IOCs pasted or described inline:** don't attempt them all inline. Ask the user to upload a CSV (or other file) instead — 15 is the line where inline chat output (a markdown table) stops being a good format and a proper file becomes the right tool. Don't silently truncate to 15 and drop the rest; say why you're asking.
- **CSV/file upload:** read it with the file-reading/xlsx skill's guidance for CSVs. Extract the IOC values (whichever column looks like it holds them — ask if genuinely ambiguous) and process all of them, no 15-item cap — a file is exactly the right tool for a larger batch.

## Step 1 — detect IOC type client-side, don't guess it via TQL

Classify each value yourself before querying (regex/pattern matching, not a TIP call):
- IPv4/IPv6 pattern → `Address`
- Domain-shaped string (has a dot, no path/scheme) → `Host`
- Starts with `http://`/`https://` or contains a path → `URL`
- 32/40/64 hex characters → `File` (MD5/SHA1/SHA256 respectively)
- Anything that doesn't match one of these → flag it as unrecognized rather than guessing a type; ask or skip it with a note.

**Confirmed gotcha:** the TQL field for type is `typeName` (string, e.g. `"Address"`), not `type` — `type` is a numeric type-ID field and errors with `"Expected type Integer, found type String"` if you pass a string to it.

## Step 2 — batch the query by type, don't query one IOC at a time

**Confirmed working:** `summary IN ("val1", "val2", "val3")` batches multiple exact-value lookups into a single `tc_list` call — this is the efficient path. Group the user's IOCs by detected type, then run one batched query per type group:
```
typeName EQ "Address" AND summary IN ("1.2.3.4", "5.6.7.8", ...) AND (indicatorActive = false OR indicatorActive = true)
typeName EQ "Host" AND summary IN ("evil.com", "bad.net", ...) AND (indicatorActive = false OR indicatorActive = true)
typeName EQ "File" AND summary IN ("<hash1>", "<hash2>", ...) AND (indicatorActive = false OR indicatorActive = true)
```
An IOC that isn't in TC at all simply won't appear in the results (confirmed live: a deliberately-unknown value was correctly absent, no error, no false match) — the absence itself is the answer for that one.

**Critical: always include `(indicatorActive = false OR indicatorActive = true)` — indicator queries default to active-only, and that default silently hides exactly the IOCs most worth flagging.** Confirmed live: `tc_list` on `indicators` auto-injects `indicatorActive=true` when the query doesn't specify it (visible in the returned pagination URL). This means an IOC TC has already evaluated and marked inactive — most commonly because its score was too low or it's a known false positive — won't show up at all under the default query, and would incorrectly read as "not found in TC." Confirmed with a real case: `8.8.8.8` (Google's public DNS, an obvious false-positive candidate) returned **nothing** under the default active-only query, but with the override returned a real record — `active: false`, `threatAssessScore: 97` (very low), `calScore: 0` — a **confirmed false positive already known to TC**, a materially more useful answer than "not found." Always use the override for IOC lookups, even though a plain default query is fine elsewhere in this skill.

## Step 3 — request the right fields in one call

Always request `fields=threatassess,associatedGroups,tags,geoLocation,dnsResolution,whoIs` together — it's safe to request all of these regardless of IOC type. Confirmed live: fields that don't apply to a given type (e.g. `dnsResolution`/`whoIs` on an `Address`) simply don't appear in that result, no error. This means one field set works for a mixed batch of IPs, hosts, and hashes without needing type-specific requests.

What each gives you:
- **`threatassess`** → `threatAssessScore`, `calScore`, and related fields — the confidence signal (see `ioc_scoring_and_topic_queries.md`).
- **`associatedGroups`** → which Reports/other objects reference this IOC — the context signal (how isolated or well-documented it is).
- **`tags`** → any malware-family/campaign tags applied.
- **`geoLocation`** (Address/Host) → country, ASN, registering org — confirmed populated for indicators with geo data.
- **`dnsResolution`**/**`whoIs`** (Host) → only populated when `hostDnsActive`/`hostWhoisActive` are true (confirmed: **the TQL filter field names are `hostDnsActive`/`hostWhoisActive`, not `dnsActive`/`whoisActive`** — those are the JSON response field names, a `name`-vs-`summary`-style mismatch). When active, these can return a large history of past resolutions/WHOIS records — **don't dump all of it**. Report the fields, don't reproduce them: for WHOIS, note registrant, creation/expiry dates, and how recently it was last updated; for DNS resolution, note the most recent resolved address and when. Never paste a raw WHOIS text blob into the output.

## Step 4 — assemble one row per IOC, with three possible states, not two

For every IOC the user gave, produce one row. There are three meaningfully different outcomes, not just "found"/"not found":
- **Not in TC at all** — no record exists. State this plainly.
- **In TC and active** — a live, current indicator; report its score/context as usual.
- **In TC but inactive** — TC has already evaluated it and deactivated it, most often because the score was too low or it's a known false positive (see the `8.8.8.8` example in Step 2). **Report this explicitly as "known false positive" or "deactivated," not as "not found."** This is one of the most useful answers this workflow can give — it tells the user their IOC isn't a mystery, it's already been triaged.

Columns to include: IOC value, type, status (not in TC / active / inactive-confirmed-FP), ThreatAssess score, CAL score, confidence/rating, owner(s) it appears under (multiple rows for the same IOC value across different owners means multiple feeds independently reported it — note that as a signal, don't just show one), associated-report count (context — an isolated IOC with zero associations is weaker evidence than one tied to several reports), and a short geo/WHOIS/DNS note where relevant (latest record only — see Step 3).

## Step 5 — output format matches input format

- **Input was pasted/typed in chat (≤15 IOCs):** output as a markdown table directly in the reply. No file.
- **Input was a CSV/file upload:** output as an enriched CSV — same source rows, with the lookup columns appended — not a markdown table. Present it via `present_files` like any other generated file in this skill.

## Citation/linking

Apply the same discipline as everywhere else in this skill (`citations_and_links.md`): link IOCs that carry real findings (high score, multiple associations) to their `webLink`; a long batch of "not found" or low-signal rows doesn't need individual links.

# Report-quality rubric (LLM-as-judge) for report-generating agents

Use when comparing or scoring the REPORTS an agent writes (A/B of two agent versions, before/after a prompt or retrieval change, run-to-run consistency). Not for routing (SKILL.md section 3) or for search results (section 17, 0/1/2 item labels).

## 0. Design rules (what makes the verdict trustworthy)
1. **Pairwise and blind.** Same request, same run number, two systems, random A/B order; the key is written to a file the judge is told not to open. Prefer the per-pair preference over absolute scores (judges calibrate themselves differently).
2. **Judge one request per judge**, with the request text and today's date supplied. Never let a judge see the system names or prompts.
3. **Hold everything else equal or say so.** If the two agents differ in more than the thing under test (prompt version, output-token cap, retrieval), the result is a bundle effect. State the confound in the report; the clean test changes one thing.
4. **>= 3 runs per request per system.** LLM output varies; report "N of M runs", not one sample.
5. **Capture outputs programmatically** (full text, conversation id, seconds, status), not by screen-scraping; keep the raw JSON and a rendered `.md` per run.
6. **Verify against the platform, not the report.** The judge must check specific claims with read-only API calls (section 3 below). A fluent report that cites things the platform does not hold is the main failure to catch.
7. A different judge model, or a second pass on 20-30% of pairs, measures judge agreement. Spot-check ~10% of verdicts by a human analyst. Report both numbers. The general method for building, calibrating and monitoring a judge (binary failure-mode labels, two-annotator human ceiling, confusion matrix, repeat-run consistency, drift checks) lives in `playbook-eval` (`references/judge_calibration.md`); this file keeps only what is specific to scoring reports. Treat the defect list in section 2 as the primary, binary-style signal and the 1-5 scores below as a secondary one.

## 1. Score each report 1-5 on five dimensions (anchored)
| Dim | 1 | 3 | 5 |
|---|---|---|---|
| **Request fit** | Wrong audience/format, ignores requested sections or timeframe | Mostly right; one requested element missing, renamed or out of order; some off-window material presented as in-window | Audience, format, requested headings (in order, with their names) and timeframe all honoured; off-window material labelled as background |
| **Groundedness / accuracy** | Contains claims the platform data contradicts or cannot support; invents actors/IOCs/dates | Mostly supported; a few unverified figures or one mis-dated item; hedging present | Every checked claim supported; dates match the source; analytic judgements labelled as assessments; gaps stated |
| **Usefulness / insight** | Generic profile that could be written without the platform data | Relevant facts but little synthesis; misses obvious in-window items | Prioritised, actionable for the stated audience; uses the platform's most relevant items; cross-source synthesis |
| **Clarity / concision** | Rambling, repetitive, wrong register | Readable but padded or uneven | Tight, scannable, audience-appropriate; no internal jargon |
| **Completeness** | Cut off mid-sentence, or required section missing/empty | Complete but one section thin without saying so | Ends cleanly; every requested section present; coverage and gaps stated honestly |
Do not average away a blocking defect: truncation or a missing requested section caps Completeness at 2 and Request fit at 3.

## 2. Defects (list every one, with severity)
| Sev | Examples |
|---|---|
| **Blocker** | Truncated output; requested section absent; fabricated entity/IOC/CVE/attribution; wrong audience layer |
| **Major** | Mis-dated claim presented as in-window; claim contradicted by the platform; missed in-window high-relevance items the platform holds; states "no data" when matching data exists |
| **Minor** | Unverifiable figure from a body the judge cannot search; section renamed; padding; formatting glitch |
| **Leak** | Internal wording ("in the data", "the platform's X object", step/check names, mentions of search modes, scores, merging or duplicates) |
Report counts per severity per system, not just a mean score.

## 3. Claim-check protocol (mandatory)
- Per report pick 3-5 of the most checkable specific claims: named source/report titles, CVE ids, actor names and aliases, dates, hashes/IOCs.
- Check with read-only GET calls on the target instance (credentials from the env file, never echoed). Summary/name search matches titles only, so ALSO fetch the description of candidate objects when a claim is body-only (`fields=description`), otherwise mark it "unverifiable" rather than "not found".
- Record each claim as `supported | partly | not found | unverifiable` with the object id used. Never write to the platform.
- Also check the reverse (recall): for an identifier-driven request (CVE, actor, technique), query the platform for objects tagged/associated with it and note relevant in-window items the report missed.
- Compare dates to the object's publish/added date; a source's headline date is not always its event date.

## 4. Consistency and reliability (scripted, no judge needed)
- Completion rate and time; routed to the intended agent; ended cleanly (last char is sentence/table end, not mid-word); requested headings present (regex on the heading list).
- Run-to-run consistency per request: pairwise word-set Jaccard across the runs, plus length spread. Low overlap with stable quality is fine (different valid angles); low overlap with swinging quality, or a pair where the preferred run flips, is the signal.
- Count leaks with a banned-phrase regex list kept per agent.

## 5. Calibration set (do once per agent family)
Keep 6-10 reports with an analyst's 1-5 scores and defect lists, ideally labelled independently by two analysts so their agreement shows the ceiling (see `playbook-eval` `references/judge_calibration.md`). Run the judge on them first; if it differs by >1 point on any dimension on more than a quarter of items, or misses defects the analysts agreed on, tighten the anchors before the real run. Re-use the set whenever the judge prompt or judge model changes, and re-run the judge on identical input a few times to check its verdicts do not flip.

## 6. Output
Per request: preferred side per run (count), mean score per dimension per system, defects per severity, claim-check tally (supported / partly / not found / unverifiable), truncation count, consistency numbers. Then: a headline, the confounds, the top fixes by evidence, and what was NOT checked. Keep raw judge JSON beside the report.

## 7. Judge prompt skeleton
"You are a blind evaluator. Files X_runN_A.md / X_runN_B.md are two systems answering the same request: <request> (today is <date>). Do not open any other file. For each pair and side: score the five dimensions (anchors below), list defects with severity, check 3-5 specific claims against the platform with read-only GET calls (do not print credentials, do not write), pick the preferred side with a one-sentence reason. Write JSON to <path>: pairs:[{run, A:{scores,defects,claims_checked}, B:{...}, preferred, reason}]. Reply with a 3-line summary." (Paste section 1's anchors and section 2's severity table.)

## 8. Practical notes from running this at scale
- Start all chats of a batch together only if you will do the same for the other system; late routing (conversation status null for a minute or two) appears under load and inflates latency.
- A "done" test must require a non-user message AND a terminal status; a null status is not done.
- A judge that only has title search will under-report body-only claims; give it the description fetch or mark claims unverifiable.
- Output-token caps: a model that spends tokens on reasoning can truncate long reports far below the cap's character equivalent. Always check the END of every report; raise the cap and re-test before comparing quality.

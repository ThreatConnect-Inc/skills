# Retrieval / search evaluation adapter

Use when the question is "does retrieval mode A return better source material than mode B" (keyword vs semantic/hybrid, before vs after a search-engine update, different Knowledge options) rather than "does the agent behave". It isolates search quality from generation quality, runs with no browser, and is cheap because everything except the relevance labels is scripted. Helper: `references/retrieval_eval.py` (stdlib only: `pool` builds judge inputs, `score` computes all metrics).

## 1 Harness
Build a webhook playbook (see `playbook-builder`, "Retrieval-eval echo harness") whose body takes `{"query", "mode", "start"}`, runs the Knowledge/search item for that mode, and has a Base Agent at temperature 0 only echo what it was given (id, type, name, date, score, tags). Add one mode per configuration under test (e.g. `keyword`, `hybrid`, `combo`). The webhook endpoint UUID changes every playbook version: re-read it before each run and record the version. Verify echoed ids against the API once (the echo is an LLM).

## 2 Query set design
Aim for 20+ requests covering: named entity, alias of an entity, group/family name, exact identifier (e.g. a CVE), product with news, concept with no entity, multi-heading request, vague one-word topic, real chat-style questions with audience wording, and one out-of-domain control (should return nothing relevant). Keep the exact wrapper wording of production requests so wrapper words that pollute matches show up. **After any fix or tuning, write a fresh held-out set of the same shape and run that too**: a first set that looked good for the new option (hybrid ahead on the tuned set) reversed on the held-out set (hybrid behind overall, ahead only on concept/multi-heading requests). Never tune a threshold and report on the same set.

## 3 Run
Run every query in every mode, a few in parallel, writing one file per (case, mode, repeat) and skipping files that exist so a re-run resumes. Treat HTTP errors and empty 2xx bodies as failures. Keep old results untouched and write new runs to a new directory.

## 4 Judge (the only LLM step)
`retrieval_eval.py pool` writes unique (case, id) items across modes as shuffled-by-case judge inputs (judges never see which mode returned an item). Give each judge agent about 200 items with titles, tags and descriptions (up to 600 chars), the 0/1/2 rubric (0 unrelated or matches only wrapper words, 1 related/indirect, 2 directly about the request), and ask for an item-specific reason of at most 12 words. Rules learned the hard way:
- Reuse existing labels by (case, id) and judge only new items; when old and new items are compared, judge them in one pool if you can (separate judge batches drift).
- After each judge returns, verify the output file exists, its keys equal the input pids, and every label is 0/1/2. One judge reported success without writing its file; another labelled a different batch's items. Do not trust the hand-back text.
- Judges tend to emit templated reasons per label tier. Spot-check 10-15 random items per run, and for entity requests check labels against the text with a script (items containing the entity name labelled 0, items without it labelled 2).

## 5 Score (scripted)
`retrieval_eval.py score <results_dir> "<labels_glob>"` prints precision at 5/10/16 per mode, a per-case table, score-band calibration for scored modes, and a merge simulation (semantic results above a score threshold first, then keyword). Report: mean precision per mode with n, wins/ties/losses per request, the cases where each mode fails, whether the control returns results, result counts versus the requested limit, and share of results below a useful score. Compare modes within one judged set; do not compare absolute numbers across sets. A mode can lead at the top 5 and trail at the top 16 (long noisy tail), so report both depths.

## 6 Traps
- A combined mode that attaches two search items does not de-duplicate and its first N depends on item order; simulate merges in the scorer instead.
- Keyword-generator output varies run to run: a single run per request is a sample, not a measurement; repeat a few cases if a decision hangs on them.
- Out-of-domain controls: if the harness lacks the production guard, the search runs on the error text; note it.
- Wrapper words ("brief", "analyst", "report", "weekly") matching titles is a retrieval defect worth counting separately.
- Write findings for the search owner with ids per case; the method belongs here, instance-specific findings do not.

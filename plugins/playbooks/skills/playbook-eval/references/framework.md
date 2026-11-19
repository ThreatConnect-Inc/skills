# Eval framework (layers, suites, gates)

Applies to any LLM-agent playbook. Answers three questions with evidence whenever the agent, prompt, template or platform changes: did anything break (regression), is it good (quality against a stated bar), is it dependable (reliability, latency, cost).

## Principles
1. **Test the playbook, not the UI.** Drive the real trigger (webhook, event, chat API) and read the execution status; UI banners can show false failures. Keep a tiny UI smoke set for the front end itself.
2. **Frozen inputs.** Fixtures must not drift.
3. **Cheapest check first.** Deterministic checks gate; programmatic grounding next; the LLM judge only on outputs that pass.
4. **Every fixed bug becomes a permanent case.**
5. **Flakiness is a metric.** Repeat each case N times and report a pass rate, never one run.
6. **Everything is versioned:** agent version, instance, model per job, fixture version, harness version.
7. **Separate judge from generator,** fixed prompt, low temperature, calibrated against two human annotators (with their agreement as the ceiling) before it gates. See `judge_calibration.md`.
8. **Split the data and lock the test set.** Tune prompts on a train set, pick between candidate versions on a validation set, and score the final version once on a locked test set. Tuning against the test set makes every number optimistic. Watch for leakage: near-duplicate items across splits, context the agent would not have in production, and repeated tweaks driven by test results.
9. **Sample size sets the margin of error.** Rare errors need many cases; halving the margin of error takes about four times the samples (for a 5% event and recall near 90%, 100 cases gives roughly +/-26 points on recall and 400 gives roughly +/-13). The suites below are smoke and regression sizes, not statistical evidence; say so when reporting a rate from them.

## Flow
```
case file -> runner -> trigger -> execution lookup (status, times)
          -> artifact capture (output + step logs if available)
          -> L1 deterministic -> L2 grounding -> L3 judge -> L4 reliability/cost
          -> result JSON per case -> scoreboard (suite x version)
```

## Case schema
```
id, title, suite, tags[], agent_version_min, fixture (pool + version)
input (exact trigger payload)
expect: must_succeed, layer1[], layer2[], rubric[], golden
repeats: N
origin: bug-id | requirement-id | exploratory
```
Result: `case_id, run_id, agent_version, instance, started, duration_s, execution_id, status, checks{}, judge{}, tokens, cost, artifact_path`.

## Layers
- **L1 Deterministic (no LLM):** execution succeeded; under time budget; output non-empty and parses; required sections present; no leakage (`undefined`, `null`, `NaN`, template syntax, unresolved variables, raw tool errors, prompt text, stray comment fragments); format constraints; designed zero-input message; countable instructions obeyed.
- **L2 Grounding (programmatic):** every entity, id, number and link exists in the input; prose counts match data; excluded items are absent; duplicates merged; links resolve; no out-of-scope or other-tenant data.
- **L3 Judge (binary pass/fail per failure mode, with a written reason each):** build the rubric from the failure modes the agent actually shows (faithfulness/unsupported claims, missed relevant items, missing sections, format fit, instruction adherence, safety/scope), each judged independently. Binary labels have clearer boundaries than 1-5 scales; a 1-5 score may be kept as a secondary signal. The judge sees the input pool, the output and the rubric. Before it gates, it must approach the human agreement ceiling (two annotators, confusion matrix, repeat-run consistency), and it is re-measured on any change and on a schedule: see `judge_calibration.md`.
  - **Judge evidence:** the judge must see what the agent actually received, not only what it cited: the retrieved records, including titles of associated or linked objects the agent can see. Without them the judge marks supported claims unsupported and produces false hard-gate failures. Worked example: after adding associated-object titles to the judge input, the same answers lost most recurring gate failures and the ranking of two prompt versions flipped. Reproduce the retrieval with a harness that calls the same search step with the parameters the agent logged for that question.
  - **Calibration:** expect an LLM judge to score the middle value whenever it cannot verify a claim, so accuracy has a low ceiling and date or recency errors slip through. Human reviewers will often fail noticeably more answers on accuracy than a judge that cannot verify claims. Give human reviewers the same ground truth as the judge (the records the agent received); otherwise they grade the data and linked source articles, not the agent. An alert's date is often when it was seen, not when the event happened.
- **L4 Reliability and cost:** pass rate over N repeats; latency p50/p95; tokens and cost per run; per-step failure counts; known-flaky cases get N=10.

## Suites
| Suite | Size | When | Layers |
|---|---|---|---|
| Smoke | 3-5 | every push or activation | L1 |
| Regression | 10-20 | before release | L1-L2, N=3 |
| Edge | about 10 | before release | L1-L2 |
| Quality | about 10 | prompt, model or agent change | L2-L3 |
| Adversarial (optional) | 5-10 | before release | L1-L3 (prompt injection in input data, out-of-scope asks) |
| UI smoke | 3 | weekly | manual/browser |

## Gates (starting defaults, tune per agent)
Smoke and all L1: 100%. Regression at or above 95% across repeats, zero known-bug regressions. Quality: judge means at or above 4.0 on faithfulness and relevance, no drop above 0.3 against the last release, zero hallucinated entities. Latency p95 within budget; a cost increase above 20% needs a written note. A failed gate blocks release; a waiver needs a named owner and a reason.

## Reporting results
- **Same samples for every variant.** Compare versions on identical cases; silently dropping hard cases from one variant makes it look better.
- **Never report accuracy alone.** When a critical error is rare, high accuracy can hide zero recall on it. Report recall and per-class or per-failure-mode results, and macro averages (unweighted per class) when classes are imbalanced; micro averages are dominated by the frequent class.
- **Floor and ceiling.** Give a floor (a naive baseline: rules, regex, the existing system) and a ceiling (human performance). Do not chase scores above the ceiling.
- **Benchmark more than one model** where the platform allows, and keep a tested fallback so a deprecation, degradation or price change does not leave the agent stranded.
- **Production footprint:** expected volume, latency, estimated cost per day, and a maintenance plan (eval cadence and owners).
- **Audit flipped cases** (pass in one version, fail in the other): they show what a change really did.

## Triage of a failing case
Logic gap (fix the agent), model non-determinism (raise N, tighten the prompt, lower temperature), or bad ground truth (fix the case). Record which in the result.

## Platform notes (TIP)
- Execution lookup: `GET /api/v3/playbook/executions` filtered by `playbookXid` (not `playbookId`, which changes on every push), `status`, `startedTime`. Failed runs have `failedTime`, not `completedTime`.
- Step-level inputs, outputs and logs come from the internal API, which needs a browser session. See `playbook-builder`'s execution-log notes.
- After an API push and activate, a Designer disable/refresh/enable may be needed before a run if you want execution data visible there.

# Agentic efficiency review

Look for ways to make the agent cheaper, faster or more reliable without hurting quality. Evidence first: use execution logs (status, step duration, tokens) and eval results, not intuition.

## Method
1. **Map the run:** every job in order, which are parallel, which are on the critical path (the slowest chain sets total time), and each job's input and output size.
2. **Measure where time and tokens go:** per-job duration and tokens from execution logs; if logs are not readable, say so and estimate from prompt size and output cap.
3. **Walk the levers below per job** and record expected gain, risk, and how to verify it with the eval.
4. **Rank by gain over risk.** Propose, do not apply; changes go through `playbook-builder`, then re-run the suites.

## Levers

| Lever | When it applies | Check it with |
|---|---|---|
| **Move work out of the model** (counts, sorting, joins, dedup keys, URL building, slot arithmetic, formatting) into JMESPath, TQL or templates | Any job that counts, formats or looks up | L1 and L2 checks; faithful numbers |
| **Retire a model job** that a template now covers | A job that is inactive, redundant, or only reshapes data | Output diff over repeated runs |
| **Payload ladder** (identity, digest, synthesis, full object): pass each job the smallest level that serves it; never pass raw full objects to a model | Large or heterogeneous result sets | Token counts; faithfulness unchanged |
| **One global pass before sharding** for anything that needs to see everything (dedup, clustering, ranking) | Parallel workers cannot see each other | Duplicate rate in output |
| **Parallelise independent jobs; shorten the critical path** | Sequential jobs with no data dependency | End-to-end p50/p95 |
| **Right-size output caps** | Caps far above real output (wasted budget) or too tight (truncated JSON) | Truncation count; actual output length |
| **Lower temperature on rule-following jobs** (parsers, planners, builders: about 0.1-0.3); keep higher only for open prose | Rule drift between runs | Pass rate over N repeats |
| **Schema gate between model hops** with a "slice unavailable" fallback instead of failing the whole run | Intermittent malformed or truncated JSON | Failure rate, partial-output rate |
| **Shared prompt fragments** (one style or rules block referenced by all jobs) | Several jobs restate the same rules and drift | Rule consistency across jobs |
| **Prompt diet** | Very long prompts with rules the job never uses; per-format dead branches | Output quality at equal or lower tokens |
| **Per-job model tier** | See `model_selection.md` | Trial |
| **Caching and incremental runs** (store prior results, process only new items) | Scheduled runs over a sliding window | Cost per run over time |
| **Cheaper checks first** | Judge or heavy steps run on outputs that fail basic checks | Share of runs reaching L3 |
| **Iterate on a small model with cached intermediate outputs**, switch to the target model for the final run | Prompt or rubric iteration where each run re-pays for unchanged upstream steps | Cost per iteration; final-run quality |
| **Second prompt-pruning pass once the prompt works**, only keeping changes that preserve quality | Prompt has grown by accretion | Quality at lower tokens, audited on flipped cases |

## Reliability patterns
- Prefer deterministic assertions over more prose rules; rules a model obeyed once may be broken next run.
- Give workers generous token caps and say "work silently, output only JSON"; extract the JSON defensively in the template.
- Make degradation graceful: one failed slice reports "unavailable" rather than failing the run.

## Output
A ranked table: lever, job, expected gain (time, tokens, failures), risk, verification, effort. Mark anything unmeasured as an estimate.

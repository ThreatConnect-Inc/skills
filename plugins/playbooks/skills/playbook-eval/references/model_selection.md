# Model-selection review (per job, evidence-based)

Goal: for each LLM job, say whether the current tier is right, what could change, and how to prove it. Platform tiers (for example fast, balanced, powerful) usually map to a small, a mid and a large model at a fixed reasoning level. Confirm the mapping and that reasoning level cannot be changed before comparing.

## Procedure
1. **Inventory and decompose:** `job_decomposition.md`.
2. **Gather benchmark data for the mapped models at the platform's reasoning level** (never mix reasoning levels). Use sources whose terms allow your use: provider model cards, papers, evaluation reports you ran, or numbers the user supplies. Do not scrape leaderboards or other sites with scripts or bots, and do not copy a third party's data into published material; many sites forbid both. If the user supplies the numbers, ask which model, reasoning level and benchmark each one is for. Put them in a CSV or JSON file and compare them:
   ```bash
   python3 -I scripts/model_compare.py --file models.csv --sort intelligence --winprob <elo_column>
   ```
   A missing number means "not available", never zero. Say what could not be found.
3. **Map each job's skill to the benchmark(s)** in `job_decomposition.md` and read the gaps between tiers, not the absolute scores.
4. **Rank options per job** (keep / try cheaper / try stronger) with confidence, the evidence, and the risk.
5. **Design the trial** (below). Recommend nothing as final before it runs.

## How to read the numbers
- **Gaps matter, not levels.** A tier that is level with the next one up on the relevant benchmark is a downshift candidate; a large gap on the relevant benchmark is an upshift candidate.
- **Elo to win rate.** For Elo benchmarks (GDPval-AA, Briefcase), expected win rate of A over B is `1 / (1 + 10^((B-A)/400))`; `scripts/model_compare.py --winprob <column>` prints it. About 50 Elo is a small edge, 250 a large one.
- **Per token vs per task.** Price per token is the platform-facing cost; "cost per task" also includes the model's own reasoning tokens. A larger tier may cost 2x per token but 3x per task. Use the platform's own pricing if known.
- **Latency.** Benchmark "time per task" comes from long agentic tasks and overstates single-call latency. For a job producing N output tokens, estimate time as N divided by output speed, plus reasoning, then check the job's position on the critical path. Parallel jobs only matter through the slowest one.
- **Composite index vs sub-benchmarks.** The overall index is dominated by reasoning, coding and agentic work. Use sub-benchmarks that resemble the job.
- **Hallucination counterweight.** Larger models are often more accurate but answer more when unsure (lower non-hallucination). The benchmark tests recalled facts, not grounding in supplied data, so treat it as a risk flag for inference-heavy jobs and test faithfulness directly in the trial.
- **Instruction following may be missing** for newer models; do not infer it from other scores without saying so.

## Trial design
- One job changed at a time; everything else held constant (same fixtures, same version).
- At least 3 renders per scenario per variant (single renders are not evidence).
- Score with L1 deterministic checks, L2 grounding and the L3 judge (a different model from the generator; see `framework.md`), plus schema failure count, end-to-end time and cost.
- Decide in advance: the win condition (for example quality at or above current, failures not higher) and the cost/latency cap.
- Record the variant tier per job in the scoreboard so results stay comparable.

## Decision rules of thumb
- Keep the current tier when the relevant gap is small or the failure mode is structural (malformed JSON is fixed by a schema gate and lower temperature, not a bigger model).
- Try a cheaper tier for narrow, schema-fixed, low-stakes jobs that are not on the critical path or a single point of failure.
- Try a stronger tier for the one or two jobs where judgement and prose quality set the perceived quality of the output.
- Never change several jobs' tiers in one release.

## Worked example (anonymised, data fetched 2026-11-13; re-fetch before reuse)
Medium reasoning, three tiers. Long-context: 77 / 76 / 84. Professional deliverables (Elo): 1283 / 1329 / 1593. Multi-step structured tasks: 29 / 55 / 61. Non-hallucination: 60 / 50 / 33. Reading: the small tier is level with the mid tier on long-context and close on deliverables (mid wins about 57%), so extraction jobs are cheap-tier candidates; it is far weaker on multi-step structured tasks, so rule-heavy planner and builder jobs stay mid. The large tier wins deliverables about 82% of the time, so the single most judgement-heavy synthesis job is the upshift candidate, with a faithfulness check because of the lower non-hallucination score. Latency impact was small once measured per output token.

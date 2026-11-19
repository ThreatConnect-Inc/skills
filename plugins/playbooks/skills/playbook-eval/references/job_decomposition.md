# Splitting an agent into jobs and naming the skill each needs

Model selection only makes sense per job. A pipeline of 8 jobs rarely needs one tier for all of them.

## Steps
1. Inventory the LLM jobs (`scripts/job_inventory.py`). Ignore inactive jobs.
2. For each job record: what goes in (size, shape), what comes out (schema, length), what makes it fail, and where it sits (on the critical path or parallel; one of many, or a single point of failure).
3. Remove what is not a model task. If the job counts, joins, sorts, formats or builds links, it should move to code first (see `efficiency_review.md`).
4. Name the **primary skill** and the **failure mode that matters** (table below).
5. Record the job-by-job table in the review; it feeds `model_selection.md`.

## Skill taxonomy and the public benchmarks that approximate each

| Skill the job uses | Typical TIP jobs | Failure mode that matters | Benchmarks that approximate it |
|---|---|---|---|
| Free text to small structured config, classification | request/guidance parsers, routers | Wrong value, text around the JSON | Instruction following (IFBench, where published), AutomationBench |
| Fill a fixed schema | metadata or title-block jobs | Almost none | Any tier; cheapest that parses |
| Rule-based decisions from small input, schema-exact JSON | section or step planners | One bad plan breaks all downstream jobs | AutomationBench, instruction following |
| Extraction and normalisation over long input | data synthesizers, enrichment summarisers | Dropped or mangled fields | Long-context reasoning (AA-LCR), multi-document synthesis (MLCR) |
| Synthesis and professional prose | executive summaries, narratives | Generic or unfaithful summary | GDPval-AA, AA-Briefcase, GDP.pdf |
| Inference beyond the data, calibrated judgement | gaps, recommendations, caveats | Fabrication, over-confidence | AA-Omniscience non-hallucination (a risk flag, see caveat), Harvey-style hallucination-checked deliverables |
| Strict schema transformation, long structured output | section/page builders | Truncated or malformed JSON | Instruction following, output speed, token cap fit |
| Multi-step tool use | agents with tools, triage, case creation | Wrong tool, guardrail violation | AutomationBench, tau-bench variants, EnterpriseOps, Terminal-Bench |
| Query or expression writing (TQL, JMESPath, code) | query builders | Valid syntax, wrong meaning | SciCode, LiveCodeBench, FrontierCode |

Benchmarks are general-purpose approximations. When the exact benchmark is not published for a model, say so and use the nearest one with its limits stated.

## Template for the review table

| Job | Input | Output | Primary skill | Failure mode | Critical path? | Current tier/temp | Candidate tier | Evidence |
|---|---|---|---|---|---|---|---|---|

# Designing an eval up front

Do this before or while building an agent. It costs an hour and makes every later eval, model review and efficiency pass cheaper, because the agent is built to be measured.

## 1. Per-agent instantiation (fill in; keep it next to the agent's docs)

1. **Trigger and contract.** How it is called, the exact payload, the output type, where the output is read.
2. **Input dimensions.** The variables that change behaviour (format, audience, data basis, size of result set, language, optional parameters). These drive the test matrix; sample them pairwise, not as a full cross product.
3. **Outputs and invariants.** What must always be true of the output (parses, required sections, no placeholder leakage, counts match). Each becomes a deterministic check.
4. **Grounding sources.** What data every claim must be traceable to (ids, numbers, links, names). Each becomes a programmatic grounding check.
5. **Quality rubric.** Dimensions, weights, and what a 1, 3 and 5 look like (faithfulness, relevance/prioritisation, completeness, format fit, actionability, clarity, instruction adherence, safety). A report-quality rubric exists in `playbook-qa`.
6. **Fixtures.** Frozen pools (tag-based seeded data, never "last 7 days" on live data), where they live, how they are versioned.
7. **Known failure modes.** Each becomes a named regression case. Start with the ones you already expect: empty input, one item, very large input, special characters, conflicting instructions.
8. **Budgets and footprint.** Latency, cost, concurrency limit, plus expected run volume and estimated cost per day.
9. **Gates.** Starting defaults are in `framework.md`; state any overrides.
10. **Owners and cadence.** One for cases and golden files, one for the judge and its calibration set, and how often the eval and the judge are re-measured.
11. **Data splits and ground truth.** Which cases are train (free to tune on), validation (choose between versions) and a locked test set used once; written annotation guidelines; two human annotators on an overlap set. Check the splits for leakage (near-duplicates, production-unavailable context).
12. **Baseline floor and human ceiling.** The naive or existing system to beat, and the human agreement level that caps what is worth chasing.

## 2. Design the agent to be evaluable

- **One job, one skill.** Jobs that each do one thing can be tiered, tested and replaced separately. A job that does five things hides which one failed.
- **Checkpoints between model hops.** A deterministic schema check after each model step turns a silent corrupt output into a flagged, attributable failure.
- **Counts and links computed, not written.** Pass exact numbers into prompts; build URLs in templates. The model copies, never counts or invents.
- **Stable identifiers.** Carry item ids through every stage so grounding can be checked end to end.
- **Versioning in the output or run record.** Agent version, model tier per job, fixture version, so a result is comparable later.
- **Step logs reachable.** Know in advance how to read per-job inputs, outputs and errors (see `playbook-builder` execution-log notes); eval triage depends on it.
- **A designed zero-result and failure path.** "No qualifying data" and "slice unavailable" outputs are part of the contract, so they can be asserted.

## 3. Maturity path (do the earlier steps before the later ones)

1. Runner plus deterministic checks plus a 3-5 case smoke suite.
2. Fixtures, regression and edge suites, a scoreboard.
3. Programmatic grounding checks.
4. Judge with calibration, quality suite.
5. Automatic trigger on every push or activation, trends across versions.

Hand the case list and rubric to `playbook-qa` to execute, and use `framework.md` for the layer, suite and gate definitions.

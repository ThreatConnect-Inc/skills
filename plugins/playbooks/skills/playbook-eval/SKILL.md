---
name: "playbook-eval"
description: "Design and run evaluations for agent-based playbooks in the Dataminr/ThreatConnect TIP, and use eval evidence to improve the agent. Use when designing an eval before or while an agent is built (input dimensions, invariants, grounding, rubric, fixtures, gates); setting up a regression/quality/reliability eval framework with an LLM judge; reviewing which model tier (fast/balanced/powerful) each agent job should use by splitting the agent into jobs, naming the skill each needs and matching it to public benchmarks; and finding agentic efficiencies (deterministic offload, parallelism, token caps, temperature, cost and latency). Generic across engineers and instances. Pairs with playbook-explorer (read the playbook), playbook-builder (apply changes) and playbook-qa (execute test runs, report-quality rubric)."
---

<!-- CANONICAL SOURCE: the dataminr-skills repo, plugins/playbooks/skills/playbook-eval/ . Edit only these files; if you find another copy of this skill anywhere else, do not edit it: tell the user. -->

# TIP Agent Eval

Use this skill for anything "eval" about an agentic playbook: planning how it will be evaluated, building the eval, choosing models per job, and spotting efficiency gains. It is the design and analysis layer. `playbook-qa` runs test cases through a trigger pathway and writes findings; `playbook-explorer` reads a playbook; `playbook-builder` changes it. This skill never edits a playbook: it produces evidence and recommendations, then hands changes to `playbook-builder` after the user agrees.

## 0. Pick the mode (ask once if unclear)

| The user wants... | Mode | Read |
|---|---|---|
| An eval for a new or planned agent, or "what should we test and how" | A. Design | `references/design_intake.md`, `references/framework.md` |
| To stand up the framework: cases, fixtures, runner, judge, scoreboard, gates | B. Build the eval | `references/framework.md`, `references/judge_calibration.md`; run cases with `playbook-qa` (report-specific judge mechanics are in its rubric) |
| "Are we using the right model for each step?" | C. Model selection | `references/job_decomposition.md`, `references/model_selection.md` |
| "How can this agent be cheaper, faster or more reliable?" | D. Efficiency review | `references/efficiency_review.md` |

Modes combine: a good design pass (A) already lists the jobs, budgets and invariants that C and D need, so do A first for a new agent. For an existing agent, C and D start from the inventory below.

Ask only what is missing (AskUserQuestion, one round): which agent/playbook (and its exported JSON or id), the platform's model tiers and what they map to, the quality bar and budgets (latency, cost), and what the user may change (prompts, structure, model tier only).

## 1. Common first step: inventory the agent

1. Get the playbook definition (use `playbook-explorer`, or an existing export). Do not guess its structure.
2. List its LLM jobs with `scripts/job_inventory.py` (model tier, temperature, token cap, prompt size, active or not). Note which jobs are inactive or deterministic (templates, JMESPath, TQL): those are not model decisions.
3. Read each LLM job's prompt enough to say what it actually does, then continue in the mode's reference.

```bash
python3 -I scripts/job_inventory.py playbook.json
```

## 2. Principles that apply in every mode

- **Evidence over opinion.** Every recommendation names its source: an eval result, an execution log, a benchmark with its date, or a stated assumption. Say what was not verified.
- **Deterministic first.** Anything countable, checkable, or computable belongs in code (JMESPath, templates, TQL), not a model. Evaluate and tier only what truly needs a model.
- **One change at a time, repeated runs.** LLM output varies. Compare versions over several runs per scenario, never one render.
- **Separate judge from generator.** A different model, fixed prompt, low temperature, binary failure-mode rubric, calibrated against two human annotators (their agreement is the ceiling) and checked for repeat-run consistency before it gates anything: `references/judge_calibration.md`.
- **Lock a test set.** Tune on train, choose on validation, score once on test; report recall and per-failure-mode results, not accuracy alone (`references/framework.md`).
- **Public benchmarks narrow, they do not decide.** They shortlist candidates and flag risks; only your own cases and rubric decide.
- **Read-only by default.** Do not push playbook changes, activate, or run live executions without the user's go-ahead; hand edits to `playbook-builder`.

## 3. Outputs

Write the result as a markdown review in the project (for example `reference/` or the project's docs folder) and summarise it in chat: what is done well and why, ranked options with confidence and the evidence for each, risks, and the next trial or case to run. Publish it as an artifact or doc only if the user asks for a shareable version.

## 4. Keeping this skill current

Benchmark names and published numbers change. Re-gather them for each review from sources you may use (see `references/model_selection.md`); treat a missing score as "not available", not as zero. Put new learnings in the matching `references/` file as a short entry, written for any TIP agent (no project, instance or customer specifics).

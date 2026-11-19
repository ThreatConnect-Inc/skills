# Building, calibrating and monitoring an LLM judge

Use whenever a judge will score or gate agent output. General practice for classifier and agent evaluation. The judge is itself a model: it needs its own evaluation before it is trusted, and again whenever it changes.

## 1. Rubric: failure modes, binary labels
- **Start from real samples.** Label real good and bad outputs, write down why each bad one is bad, and turn each reason into a yes/no question. Those questions are the rubric; the labelled samples become the judge's examples.
- **Design around the errors the agent actually makes** (factual errors, repetition, unsupported claims, missing sections), not a generic quality checklist.
- **Binary labels per error type, judged independently,** instead of a 1-5 scale or good/major/minor. Scales have fuzzy boundaries, so annotators and judges tend to agree more readily on independent yes/no error types. Keep a 1-5 score only as a secondary, clearly labelled signal.
- **Give the judge the source data** as the reference for fact-checking (see `framework.md`, "Judge evidence").
- **Separate calibration data.** Calibrate the judge on a different set than the one you later evaluate the agent on.

## 2. Measure the human ceiling first
1. Have at least **two human annotators** label an overlap set independently, blind to the agent's or judge's verdicts (no anchoring) and working from written guidelines.
2. Compute **inter-annotator agreement** on the overlap. Low agreement means the rubric or guidelines are ambiguous, not that the annotators are wrong: fix the rubric first.
3. That agreement is the **ceiling**. Do not demand more from a judge than humans give each other.
4. A majority vote across several LLMs is not ground truth: models can be wrong together, so agreement between models is not proof of correctness.

## 3. Calibrate against humans
- Run the judge on the human-labelled set and compare, per error type, with a **confusion matrix**: where is it too lenient (misses real errors) and where too strict (false positives)? A single agreement figure hides this; a judge can reach 80% agreement and still miss most hallucinations.
- Iterate on rubric and judge prompt until judge-human agreement approaches the human ceiling, then freeze the version.
- Report the numbers with the judge: ceiling, judge-human agreement, confusion matrix, sample size.

## 4. Check the judge's own consistency
- **Re-run the judge on identical input** several times (for example 10). Verdicts that flip (3 of 10, say) mean the rubric, the data or the judge needs work.
- Separate the sources of variance: the data sample, the agent's generation, and the judge's verdict.
- Check known judge biases: position (A/B order; randomise it), verbosity, and self-preference (a judge from the same model family as the generator). Use a different family where you can.
- Never accept a single judge run per sample for anything that gates.

## 5. Monitor it; it is not one and done
- **Version together:** dataset, rubric, judge prompt, judge model.
- **Compare like with like:** run old and new judges on the same dataset on the same day, and compare each against the human labels (agreement delta). Look at where they disagree.
- **Re-measure on any change** to rubric, error types or judge model, and on a regular schedule (for example monthly) to catch drift.
- **Trends:** when judging past runs to see how the agent changed over time, re-judge them all with the same new judge and do not swap the agent mid-comparison.
- **Stale ground truth:** when a rubric changes (what counted as a major error yesterday does not today), correct the labels, remove examples that no longer apply, and re-measure earlier results.

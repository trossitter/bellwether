# 0004. Calibrated probabilities, not rank cutoffs

- **Status:** Accepted
- **Date:** 2026-06-02

## Context

"At risk" needs an operational definition. A ranking model would let us take the top-N riskiest subscribers, but N is arbitrary, and a rank carries no absolute meaning: the 100th-riskiest subscriber in a calm cohort is not comparable to the 100th in a volatile one, and the same rank means different things from one scoring run to the next. Raw gradient-boosted-tree scores are not probabilities either — they are monotonic with risk but uncalibrated.

## Decision

We will calibrate model scores with isotonic regression so that a score reads as an absolute probability of cancelling within the horizon, and define risk as **fixed probability thresholds** rather than a quota:

- **P ≥ 0.50 — high** (more likely than not to cancel).
- **P ≥ 0.10 — medium** (worth an intervention).

The number of subscribers "at risk" is whatever genuinely clears the bar, not a fixed top-N.

## Consequences

- **Easier:** counts mean something — 94 subscribers over 0.50 are 94 who are more likely than not to cancel; thresholds are tunable without retraining; scores are comparable across runs and cohorts; outreach volume scales to real risk instead of a fixed list.
- **Harder:** requires a held-out calibration step and ongoing calibration monitoring. A miscalibrated model makes the thresholds lie, so calibration is a gated evaluation metric, not a nicety.

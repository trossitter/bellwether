# 0002. Score the active book, train on point-in-time history

- **Status:** Accepted
- **Date:** 2026-06-02

## Context

We can only intervene on subscribers who are still active — scoring an already-cancelled subscriber would be predicting a churn that already happened. But a supervised churn model needs labeled examples of both stayers and leavers, and today's active book has no realized outcomes yet.

The data carries full subscription history, including cancellations with timestamps. That history is the only source of labels. The hazard is leakage: any feature computed using data from after the moment we are pretending to stand at would leak the outcome into the model and inflate offline metrics.

## Decision

We will score the **active book** as of the snapshot, and build training labels from **point-in-time observation windows** over history — observation dates at 365 / 270 / 180 / 90 days before the snapshot. At each observation date, a subscription is in-cohort if it existed and had not yet cancelled; its label is whether it cancelled within the horizon (30 / 60 days). Every feature is computed strictly as of the observation date, behind a leakage guard that rejects any query referencing data past that line.

## Consequences

- **Easier:** training labels are fully observed, because each window closes before the snapshot; the active book is exactly the actionable population; one history yields many labeled examples by reusing several observation dates.
- **Harder:** all feature code must be point-in-time correct — every query is bounded by the observation date and the guard enforces it. Leakage bugs here are silent and would quietly invalidate the model.
- **A definitional seam to watch:** training-cohort membership uses `CANCELLED_AT IS NULL OR CANCELLED_AT >= obs`, while the scoring cohort uses `STATUS = 'active'`. These can diverge at the edges (e.g. paused or expired states with no cancellation timestamp). Reconcile the two definitions if that gap turns out to matter.

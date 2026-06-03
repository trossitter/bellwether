# 0001. Scope modeling to the Thesis subscription line

- **Status:** Accepted
- **Date:** 2026-06-02

## Context

The partner sells on subscription across two product lines:

- **Thesis** — adult nootropic / cognitive-performance supplements.
- **Stasis** — a line that includes a children's product (Stasis Kids).

The data lake covers both: 566,743 total subscriptions, of which Thesis is 449,902 (79%). The build window was one week, and the objective was a working slice of the full motion — score → classify → intervene → dispatch → learn — running on real data, not a shallow pass over the entire base.

The two lines differ in ways that bear directly on a churn model:

- **Feature signal.** Thesis has `THESIS_FORMULAS` coverage, which supports a formula-based feature set that does not exist for Stasis.
- **Churn semantics.** Stasis purchases are partly parent-driven, carry a distinct stimulant-sensitivity profile, and sit in different household economics. The *reasons* a subscriber leaves — and therefore the archetypes and interventions — are not the same population.

A single pooled model with a `BRAND` flag would either drop the Thesis-only features or carry terms that mean different things per line, suppressing signal in both.

## Decision

We will scope the model to the Thesis line and build on its **active** subscribers. Stasis is treated as a separate problem to be served later by a sibling model on the same pipeline architecture — its own archetype taxonomy and golden set — not by pooling the two lines under a brand flag.

## Consequences

- **Easier:** a coherent feature set, churn semantics that hold across the cohort, and a faster path to a complete, honest end-to-end slice within the build window.
- **Harder / deferred:** Stasis has no coverage yet. Expanding to it is a new model — a brand-specific archetype taxonomy, a fresh golden set, and a retrain — rather than a configuration change to this one.
- **Constraint it imposes:** shared infrastructure (scoring, dispatch, the learning loop) must stay brand-agnostic so the Stasis sibling can reuse it. The externalized configuration surface (brand voice, thresholds, taxonomy, dispatch target) is what keeps that expansion a settings-and-data exercise rather than a fork.
- **Population that gets scored:** the active book at the snapshot (26,584 subscriptions on 2026-04-21). Inactive Thesis history is not discarded — it supplies the training labels via point-in-time observation windows. (The choice to score the active book while training on history is its own decision, recorded separately.)

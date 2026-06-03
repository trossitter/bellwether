# 0003. Deterministic core, ML for risk, LLM only for judgment

- **Status:** Accepted
- **Date:** 2026-06-02

## Context

An "autonomous intervention" system could be built end to end with a language model — let it score risk, decide the action, and write the message. That maximizes flexibility but trades away testability, auditability, cost control, and explainability, and it puts an irreversible, outward-facing action (messaging a real subscriber) behind a non-deterministic component. The partner needs to trust the system's decisions and tune them.

## Decision

We will divide responsibilities by what each tool is genuinely good at:

- **Deterministic code** owns scoring orchestration, archetype routing, eligibility, guardrails, and dispatch.
- **A gradient-boosted-tree model (LightGBM) + SHAP** owns risk prediction — explainable per subscriber, runs at full scale, with no fine-tuned model where a simpler one suffices.
- **The language model** is confined to the two genuine judgment calls: which intervention fits this subscriber, and what to say.

This division is what makes Bellwether an agent rather than a rules engine, without surrendering control of the parts that must be deterministic.

## Consequences

- **Easier:** routing and guardrails are unit-testable and auditable; risk is explainable through SHAP; LLM cost is bounded to drafting; failures stay localized to a layer.
- **Harder:** more moving parts than a single prompt, and the boundary has to be maintained — the standing temptation is to let LLM judgment creep into routing or eligibility, which would erode the guarantees above.
- **Forecloses:** no end-to-end learned policy. Intervention selection is rule-plus-judgment, not learned from outcomes; the learning loop tunes the inputs to that process, it is not a reinforcement-learning policy.

# Bellwether

Subscription churn prediction & autonomous intervention for a DTC supplements
partner running two product lines on a subscription model.

A *bellwether* is the lead animal whose movement foretells the flock's — the name
for a system whose job is to read leading indicators and act **before** a subscriber
cancels, rather than trying to win them back after.

Bellwether shifts TakeThesis from reactive saves to proactive prediction and autonomous intervention. It identifies which subscribers are likely to cancel in the next 30–60 days, routes each one to the most relevant intervention archetype, and drafts a personalized outreach — without requiring a human in the loop for every decision.

The design philosophy is simple: machine learning handles the prediction, deterministic code handles the routing and guardrails, and the language model handles only the judgment calls it's genuinely suited for — which intervention fits this subscriber, and what to say.

## What it does

An end-to-end pipeline, not a dashboard:

1. **Score** — point-in-time features over the subscriber base feed a calibrated
   churn-risk model with explainable per-subscriber risk factors.
2. **Classify** — each at-risk subscriber is routed to a churn *archetype*
   (price, efficacy, fatigue/overstock, life change, stimulant change, involuntary).
3. **Intervene** — an agent selects an archetype-appropriate action from several
   paths and drafts it; deterministic guardrails and a configurable human-in-the-loop
   threshold gate execution.
4. **Dispatch** — actions go through an adapter seam (simulated in the sandbox; a
   real Klaviyo/Zendesk adapter is the single production swap-point).
5. **Learn** — every action and outcome is logged back to the warehouse and feeds a
   feedback loop that tunes future scoring and intervention selection.

## Design stance

- Deterministic code owns scoring, routing, eligibility, guardrails, and dispatch.
- The model is used only for the judgment call: which intervention fits, and what to
  say. That is what makes this an agent rather than a rules engine.
- Gradient-boosted trees + SHAP for risk (explainable, full-scale), not a fine-tuned
  model where a simpler one suffices.

## Data boundary

- Reads only from the read-only `SOURCE` schema.
- Writes only to namespaced (`BELLWETHER_`) tables in the `OUTPUTS` schema.
- Credentials come from the environment, never argv or disk.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in SNOWFLAKE_PASSWORD and ANTHROPIC_API_KEY
```

`connect.sh` is a read-only Snowflake query helper for ad-hoc exploration.

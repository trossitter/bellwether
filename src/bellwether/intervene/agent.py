"""Claude-backed intervention agent for Bellwether at-risk subscribers.

The agent is the only Bellwether component that uses Claude for judgment: it
chooses the single best allowed action and drafts a subscriber-specific Thesis
message. Scoring, archetype routing, urgency assignment, action-menu bounds,
JSON parsing, and guardrail enforcement stay deterministic so dispatch sees a
contract-checked InterventionProposal. The default Thesis brand config selects
the warm voice because calibration favored messages that are specific,
non-desperate, and grounded in whether the subscriber is getting real value.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from bellwether.eval.brand_config import BrandConfig
from bellwether.eval.contracts import InterventionProposal

AGENT_MODEL = "claude-haiku-4-5-20251001"

ARCHETYPE_ACTIONS: dict[str, set[str]] = {
    "price": {"offer_discount", "explain_value"},
    "efficacy": {"share_testimonial", "offer_consult"},
    "fatigue": {"adjust_cadence", "pause_subscription"},
    "life_change": {"pause_subscription", "reduce_quantity"},
    "stimulant": {"recommend_alternative", "offer_consult"},
    "involuntary": {"retry_payment", "update_payment_method"},
}

_ARCHETYPE_DEFINITIONS: dict[str, str] = {
    "price": (
        "The subscriber may churn because the subscription cost or perceived "
        "value feels out of balance."
    ),
    "efficacy": (
        "The subscriber may churn because they are not yet seeing clear "
        "cognitive benefits or formula fit."
    ),
    "fatigue": (
        "The subscriber may churn because the cadence, routine, or repeated "
        "shipments feel like too much right now."
    ),
    "life_change": (
        "The subscriber may churn because a personal schedule, budget, travel, "
        "or routine change disrupted usage."
    ),
    "stimulant": (
        "The subscriber may churn because stimulant sensitivity, caffeine, or "
        "side-effect concerns may be affecting fit."
    ),
    "involuntary": (
        "The subscriber is at risk because of payment, billing, or account "
        "friction rather than an intentional cancellation."
    ),
}

_FEATURE_LABELS: dict[str, str] = {
    "price_float": "subscription price",
    "tenure_days": "length of subscription",
    "next_charge_days": "days until next charge",
    "order_count": "number of past orders",
    "order_cadence_days": "average days between orders",
    "days_since_last_order": "days since last order",
    "has_discount_history": "past discount usage",
    "ticket_count": "support ticket history",
    "has_adverse_event": "reported side effect",
    "has_support_cancel_reason": "contacted support about cancelling",
    "no_quiz_proxy": "no assessment on file",
}

_METADATA_FIELDS: tuple[str, ...] = (
    "tenure_days",
    "price_float",
    "no_quiz_proxy",
)

_LOGGER = logging.getLogger(__name__)


def intervene(subscriber: dict, brand: str = "thesis") -> InterventionProposal:
    """Select action and draft message for one at-risk subscriber.

    Raises GuardrailError if the agent's output fails contract checks.
    Raises ValueError if the archetype is unknown.
    """
    import anthropic
    from bellwether.intervene.guardrails import run_guardrails

    brand_config = BrandConfig.load(brand)
    archetype = str(_get(subscriber, "archetype", "")).strip()
    # Handle Enum repr "Archetype.price" → "price"
    if "." in archetype:
        archetype = archetype.rsplit(".", 1)[-1]
    if archetype not in ARCHETYPE_ACTIONS:
        raise ValueError(f"Unknown archetype: {archetype!r}")

    churn_prob = float(_get(subscriber, "churn_prob_30d", 0.0))
    urgency_level = _urgency_level(churn_prob)
    allowed_actions = sorted(ARCHETYPE_ACTIONS[archetype])
    system_prompt = _build_system_prompt(brand_config, archetype, allowed_actions)
    user_message = _build_user_message(
        subscriber,
        churn_prob,
        urgency_level,
        allowed_actions,
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    data = _parse_json_response(_response_text(response))
    if "reasoning" in data:
        _LOGGER.info(
            "Intervention agent reasoning for %s: %s",
            _get(subscriber, "subscriber_id", ""),
            data["reasoning"],
        )

    _require_fields(data, ("action", "message", "urgency_level"))
    proposal = InterventionProposal(
        subscriber_id=str(_get(subscriber, "subscriber_id", "")),
        archetype=archetype,
        action=str(data["action"]).strip(),
        message=str(data["message"]).strip(),
        urgency_level=urgency_level,
    )
    return run_guardrails(proposal)


def _urgency_level(churn_prob: float) -> str:
    if churn_prob >= 0.50:
        return "high"
    if churn_prob >= 0.20:
        return "medium"
    return "low"


def _build_system_prompt(
    brand_config: BrandConfig,
    archetype: str,
    allowed_actions: list[str],
) -> str:
    return f"""\
You are a retention specialist for Thesis, a DTC nootropics supplement brand.

Brand voice: {brand_config.tone_descriptor}
Score 5 tone reference: {brand_config.tone_score_5}
Score 3 tone reference: {brand_config.tone_score_3}
Score 1 tone reference: {brand_config.tone_score_1}

Archetype: {archetype}
Definition: {_ARCHETYPE_DEFINITIONS[archetype]}
Allowed actions for this archetype: {", ".join(allowed_actions)}

Choose exactly one allowed action and draft one subscriber-specific outreach message.
The message must be 50-500 characters, warm, specific, non-desperate, and grounded in the subscriber context.
Return JSON only, with no prose, no markdown, and no code fences:
{{"action":"<one allowed action>","message":"<50-500 chars>","urgency_level":"<provided urgency_level>","reasoning":"<optional brief private note>"}}
"""


def _build_user_message(
    subscriber: Mapping[str, Any],
    churn_prob: float,
    urgency_level: str,
    allowed_actions: list[str],
) -> str:
    lines = [
        f"Subscriber ID: {_get(subscriber, 'subscriber_id', '')}",
        f"Churn probability in 30 days: {churn_prob:.2f}",
        f"Deterministic urgency_level: {urgency_level}",
        "Return that exact urgency_level value.",
        "",
        "Top churn drivers:",
    ]
    lines.extend(_format_shap_features(subscriber))
    metadata = _format_metadata(subscriber)
    if metadata:
        lines.extend(["", "Concrete metadata:", *metadata])
    lines.extend([
        "",
        "Action menu:",
        *[f"- {action}" for action in allowed_actions],
    ])
    return "\n".join(lines)


def _format_shap_features(subscriber: Mapping[str, Any]) -> list[str]:
    features = []
    for index in range(1, 4):
        feature = _get(subscriber, f"shap_top{index}_feature", "")
        value = _get(subscriber, f"shap_top{index}_value", None)
        if feature in (None, "") or value in (None, ""):
            continue
        label = _feature_label(str(feature))
        direction = "pushes toward churn" if float(value) >= 0 else "pushes away from churn"
        features.append(f"- {label} ({feature}): {float(value):.3f}, {direction}")
    return features or ["- None provided"]


def _format_metadata(subscriber: Mapping[str, Any]) -> list[str]:
    metadata = []
    for field in _METADATA_FIELDS:
        value = _get(subscriber, field, None)
        if value not in (None, ""):
            metadata.append(f"- {_feature_label(field)} ({field}): {value}")
    return metadata


def _feature_label(feature: str) -> str:
    if feature in _FEATURE_LABELS:
        return _FEATURE_LABELS[feature]
    if feature.startswith("has_"):
        return "formula type"
    return feature.replace("_", " ")


def _parse_json_response(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"Agent returned unparseable output: {raw[:200]}")
        cleaned = cleaned[start:end]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Agent returned invalid JSON: {raw[:200]}") from exc
    if not isinstance(data, dict):
        raise ValueError("Agent returned JSON that is not an object")
    return data


def _response_text(response: Any) -> str:
    chunks = []
    for block in getattr(response, "content", []):
        text = block.get("text", "") if isinstance(block, Mapping) else getattr(block, "text", "")
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _require_fields(data: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValueError(f"Agent response missing required field(s): {', '.join(missing)}")


def _get(subscriber: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if hasattr(subscriber, "get"):
        return subscriber.get(key, default)
    try:
        return subscriber[key]
    except (KeyError, TypeError):
        return default

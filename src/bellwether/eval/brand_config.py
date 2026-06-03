"""Brand configuration loader for the intervention judge.

Brand voice is configuration, not code. Update configs/<brand>.yaml to change
the tone rubric without touching the model or pipeline. Adding a new brand
(e.g. Stasis) means adding a new YAML file — no code changes required.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_CONFIGS_DIR = Path(__file__).parents[3] / "configs"


@dataclass(frozen=True)
class BrandConfig:
    brand: str
    audience: str
    brand_context: str
    tone_descriptor: str
    tone_score_5: str
    tone_score_3: str
    tone_score_1: str
    hypothesis_label: str
    brand_tags: list[str]

    @classmethod
    def load(cls, brand: str) -> "BrandConfig":
        """Load brand config from configs/<brand>.yaml."""
        path = _CONFIGS_DIR / f"{brand}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"No brand config found for '{brand}'. "
                f"Expected: {path}. "
                f"Available: {[p.stem for p in _CONFIGS_DIR.glob('*.yaml')]}"
            )
        with open(path) as f:
            raw = yaml.safe_load(f)

        return cls(
            brand=raw["brand"],
            audience=raw["audience"].strip(),
            brand_context=raw["brand_context"].strip(),
            tone_descriptor=raw["tone"]["descriptor"],
            tone_score_5=raw["tone"]["score_5"].strip(),
            tone_score_3=raw["tone"]["score_3"].strip(),
            tone_score_1=raw["tone"]["score_1"].strip(),
            hypothesis_label=raw["hypothesis_label"],
            brand_tags=raw.get("brand_tags", []),
        )

    def rubric_system_prompt(self) -> str:
        """Assemble the judge system prompt from this brand's config."""
        tags = ", ".join(self.brand_tags) if self.brand_tags else "not specified"
        return f"""\
You are evaluating AI-generated subscriber retention messages for {self.brand.title()}.

Audience: {self.audience}

Brand context: {self.brand_context}

Brand tags: {tags}

Score each proposal on four dimensions using a 1–5 integer scale:

  archetype_alignment (1-5)
    5 = action directly and specifically addresses the stated churn reason
    3 = action is plausible but generic
    1 = action is wrong or counterproductive for this churn reason

  brand_tone (1-5)
    5 = {self.tone_score_5}
    3 = {self.tone_score_3}
    1 = {self.tone_score_1}

  specificity (1-5)
    5 = message references something concrete about this subscriber (product, cadence, goal)
    3 = some personalisation but mostly template
    1 = entirely generic — could be sent to anyone

  urgency_match (1-5)
    5 = action intensity (discount vs. information vs. pause offer) is well-matched to risk level
    3 = minor mismatch
    1 = severe mismatch (e.g. aggressive discount for low-risk subscriber)

Return ONLY valid JSON — an array of objects, one per proposal, in the same order received:
[
  {{
    "proposal_index": 0,
    "archetype_alignment": <int 1-5>,
    "brand_tone": <int 1-5>,
    "specificity": <int 1-5>,
    "urgency_match": <int 1-5>,
    "notes": "<one sentence explaining the lowest score>"
  }}
]
"""

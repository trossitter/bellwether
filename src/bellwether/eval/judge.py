"""LLM-as-judge harness for evaluating intervention proposal quality.

The judge is a separate Claude call that scores each proposal against a
four-dimension rubric. It is distinct from the intervention agent — same
model family, entirely different prompt, different job.

Brand voice is configuration, not code. Pass a BrandConfig (loaded from
configs/<brand>.yaml) to change the tone rubric without touching the model
or pipeline. Adding a new brand means adding a YAML file, not changing code.

Trust hierarchy
---------------
1. Behavior contracts (eval/contracts.py) run first and are a hard gate.
   The judge only sees proposals that passed all contracts.
2. The judge scores on softer dimensions contracts cannot enumerate:
   tone, specificity, archetype alignment quality.
3. Before trusting the judge on production output, calibrate it against
   a 30-item human-rated golden set (see calibrate()). Spearman ≥ 0.70
   is required.

Rubric dimensions (1–5 each)
-----------------------------
  archetype_alignment  Does the action logically address the stated churn reason?
  brand_tone           Matches the brand's voice — defined in configs/<brand>.yaml.
  specificity          References something concrete about this subscriber.
  urgency_match        Action intensity matches the risk level.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import anthropic
from scipy.stats import spearmanr

from bellwether.eval.brand_config import BrandConfig
from bellwether.eval.contracts import InterventionProposal

JUDGE_MODEL = "claude-sonnet-4-6"
DEFAULT_BRAND = "thesis"


@dataclass
class JudgeScore:
    proposal_index: int
    archetype_alignment: int
    brand_tone: int
    specificity: int
    urgency_match: int
    notes: str = ""

    @property
    def mean(self) -> float:
        return (self.archetype_alignment + self.brand_tone +
                self.specificity + self.urgency_match) / 4

    @property
    def dimensions(self) -> dict[str, int]:
        return {
            "archetype_alignment": self.archetype_alignment,
            "brand_tone": self.brand_tone,
            "specificity": self.specificity,
            "urgency_match": self.urgency_match,
        }

    def passes(self, mean_threshold: float = 3.5, floor: int = 3) -> bool:
        return self.mean >= mean_threshold and all(
            v >= floor for v in self.dimensions.values()
        )


@dataclass
class CalibrationResult:
    spearman_r: float
    p_value: float
    n_items: int
    passes: bool
    brand: str

    def __str__(self) -> str:
        status = "PASS" if self.passes else "FAIL"
        return (f"Calibration [{status}] brand={self.brand}: "
                f"r={self.spearman_r:.3f} p={self.p_value:.4f} n={self.n_items}")


class JudgeHarness:
    """Evaluates intervention proposals against a brand-specific rubric.

    Brand voice is loaded from configs/<brand>.yaml. To change tone assumptions
    or add a new brand, update or add a YAML file — no code changes required.
    """

    def __init__(
        self,
        brand: str = DEFAULT_BRAND,
        model: str = JUDGE_MODEL,
        mean_threshold: float = 3.5,
        dimension_floor: int = 3,
    ) -> None:
        self._brand_config = BrandConfig.load(brand)
        self._client = anthropic.Anthropic()
        self._model = model
        self._mean_threshold = mean_threshold
        self._dimension_floor = dimension_floor

    @property
    def brand_config(self) -> BrandConfig:
        return self._brand_config

    def score_batch(
        self,
        proposals: Sequence[InterventionProposal],
        shap_contexts: Sequence[dict] | None = None,
    ) -> list[JudgeScore]:
        """Score a batch of proposals in a single API call."""
        if not proposals:
            return []
        user_content = _build_user_message(proposals, shap_contexts)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self._brand_config.rubric_system_prompt(),
            messages=[{"role": "user", "content": user_content}],
        )
        raw = response.content[0].text.strip()
        return _parse_scores(raw, len(proposals))

    def score_one(
        self,
        proposal: InterventionProposal,
        shap_context: dict | None = None,
    ) -> JudgeScore:
        return self.score_batch(
            [proposal],
            [shap_context] if shap_context else None,
        )[0]

    def calibrate(self, golden_path: Path) -> CalibrationResult:
        """Validate the judge against human-rated golden proposals.

        Golden file: JSON array with keys proposal, human_mean (1–5),
        shap_context (optional). Spearman ≥ 0.70 required before trusting
        the judge on production output.
        """
        with open(golden_path) as f:
            golden = json.load(f)

        proposals    = [InterventionProposal(**item["proposal"]) for item in golden]
        contexts     = [item.get("shap_context") for item in golden]
        human_scores = [item["human_mean"] for item in golden]

        judge_scores = self.score_batch(proposals, contexts)
        judge_means  = [s.mean for s in judge_scores]

        r, p = spearmanr(human_scores, judge_means)
        return CalibrationResult(
            spearman_r=float(r),
            p_value=float(p),
            n_items=len(golden),
            passes=float(r) >= 0.70,
            brand=self._brand_config.brand,
        )


def _build_user_message(
    proposals: Sequence[InterventionProposal],
    shap_contexts: Sequence[dict] | None,
) -> str:
    parts = [f"Evaluate the following {len(proposals)} proposal(s):\n"]
    for i, proposal in enumerate(proposals):
        ctx = (shap_contexts[i] if shap_contexts else None) or {}
        churn_prob  = ctx.get("churn_prob", "unknown")
        top_features = ctx.get("top_features", [])
        parts.append(f"\n--- Proposal {i} ---")
        parts.append(f"Archetype:     {proposal.archetype}")
        parts.append(f"Action:        {proposal.action}")
        parts.append(f"Urgency:       {proposal.urgency_level}")
        if churn_prob != "unknown":
            parts.append(f"Churn prob:    {churn_prob:.2f}")
        if top_features:
            parts.append(f"Top risk factors: {', '.join(top_features)}")
        parts.append(f"Message:\n{proposal.message}")
    return "\n".join(parts)


def _parse_scores(raw: str, expected: int) -> list[JudgeScore]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end   = cleaned.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"Judge returned unparseable output: {raw[:200]}")
        data = json.loads(cleaned[start:end])

    scores = [
        JudgeScore(
            proposal_index=item["proposal_index"],
            archetype_alignment=int(item["archetype_alignment"]),
            brand_tone=int(item["brand_tone"]),
            specificity=int(item["specificity"]),
            urgency_match=int(item["urgency_match"]),
            notes=item.get("notes", ""),
        )
        for item in data
    ]

    if len(scores) != expected:
        raise ValueError(
            f"Judge returned {len(scores)} scores for {expected} proposals"
        )
    return scores

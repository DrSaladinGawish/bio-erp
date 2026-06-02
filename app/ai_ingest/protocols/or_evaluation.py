"""
OR Evaluation Protocol — Incentive House ERP
Operational Research: AHP MCDM + Sensitivity Analysis for suggestion scoring.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_ingest.models import AISuggestedTransaction, SuggestionStatus

logger = logging.getLogger(__name__)


class CriteriaWeight(str, Enum):
    HISTORICAL_MATCH = "historical_match"
    AMOUNT_CONFIDENCE = "amount_confidence"
    VENDOR_VERIFIABILITY = "vendor_verifiability"
    GL_COMPATIBILITY = "gl_compatibility"
    TAX_COMPLIANCE = "tax_compliance"
    COMPLETENESS = "completeness"


@dataclass
class ORScoreCard:
    suggestion_id: int
    overall_score: float
    approve_score: float
    amend_score: float
    reject_score: float
    criteria_breakdown: dict[str, float]
    recommendation: str
    confidence_interval: tuple[float, float]
    reasoning: list[str] = field(default_factory=list)


class OREvaluationProtocol:

    AHP_WEIGHTS = {
        CriteriaWeight.HISTORICAL_MATCH: 0.30,
        CriteriaWeight.AMOUNT_CONFIDENCE: 0.25,
        CriteriaWeight.VENDOR_VERIFIABILITY: 0.15,
        CriteriaWeight.GL_COMPATIBILITY: 0.10,
        CriteriaWeight.TAX_COMPLIANCE: 0.10,
        CriteriaWeight.COMPLETENESS: 0.10,
    }

    AUTO_APPROVE_MIN = 0.85
    AMEND_MIN = 0.60
    REJECT_MAX = 0.40

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sensitivity_variance = 0.05

    async def evaluate(
        self, suggestion: AISuggestedTransaction,
        neural_matches: list[dict] | None = None,
        extracted_entities: dict | None = None,
    ) -> ORScoreCard:
        criteria = {}

        neural_matches = neural_matches or []
        extracted_entities = extracted_entities or {}

        best_sim = max(
            (m.get("confidence", 0) for m in neural_matches),
            default=suggestion.confidence_score,
        )
        criteria[CriteriaWeight.HISTORICAL_MATCH] = min(best_sim, 1.0)

        detected_amounts = extracted_entities.get("amounts", [])
        sug_amount = suggestion.total_debit
        if sug_amount and detected_amounts:
            closest = min(detected_amounts, key=lambda x: abs(x - sug_amount))
            ratio = min(sug_amount, closest) / max(sug_amount, closest) if max(sug_amount, closest) > 0 else 0
            criteria[CriteriaWeight.AMOUNT_CONFIDENCE] = ratio
        elif sug_amount:
            criteria[CriteriaWeight.AMOUNT_CONFIDENCE] = 0.5
        else:
            criteria[CriteriaWeight.AMOUNT_CONFIDENCE] = 0.0

        vendor_id = getattr(suggestion, "suggested_vendor_id", None) or getattr(suggestion, "amended_vendor_id", None)
        v_score = 1.0 if vendor_id else 0.3 if extracted_entities.get("supplier_name") else 0.0
        criteria[CriteriaWeight.VENDOR_VERIFIABILITY] = v_score

        lines = suggestion.journal_lines or []
        has_gl = any(
            isinstance(l, dict) and l.get("coa_account_id", 0) > 0 for l in lines
        )
        criteria[CriteriaWeight.GL_COMPATIBILITY] = 1.0 if has_gl else 0.0

        total = suggestion.total_debit or 0
        tax = suggestion.total_credit or 0
        if total > 0:
            expected = total * 0.14
            tax_ratio = min(tax, expected) / max(tax, expected) if max(tax, expected) > 0 else 0
            criteria[CriteriaWeight.TAX_COMPLIANCE] = tax_ratio
        else:
            criteria[CriteriaWeight.TAX_COMPLIANCE] = 0.0

        required = ["transaction_type", "total_debit", "description"]
        present = sum(
            1 for f in required if getattr(suggestion, f, None) is not None
        )
        criteria[CriteriaWeight.COMPLETENESS] = present / len(required)

        overall = sum(
            criteria.get(c, 0.0) * w for c, w in self.AHP_WEIGHTS.items()
        )

        lower, upper = self._sensitivity_analysis(criteria)

        completeness = criteria.get(CriteriaWeight.COMPLETENESS, 0)
        approve_score = overall * (1 - (upper - lower)) * completeness
        amend_score = overall * 0.7 + (1 - completeness) * 0.3
        reject_score = 1.0 - overall

        if overall >= self.AUTO_APPROVE_MIN and approve_score > amend_score and approve_score > reject_score:
            recommendation = "approve"
        elif overall >= self.AMEND_MIN and amend_score > reject_score:
            recommendation = "amend"
        elif overall <= self.REJECT_MAX:
            recommendation = "reject"
        else:
            recommendation = "human_review"

        reasoning = [
            f"Historical match: {criteria[CriteriaWeight.HISTORICAL_MATCH]:.1%}",
            f"Amount confidence: {criteria[CriteriaWeight.AMOUNT_CONFIDENCE]:.1%}",
            f"Vendor: {criteria[CriteriaWeight.VENDOR_VERIFIABILITY]:.1%}",
            f"GL: {criteria[CriteriaWeight.GL_COMPATIBILITY]:.1%}",
            f"Tax: {criteria[CriteriaWeight.TAX_COMPLIANCE]:.1%}",
            f"Completeness: {criteria[CriteriaWeight.COMPLETENESS]:.1%}",
            f"Overall MCDM: {overall:.3f} (sensitivity: {lower:.3f}-{upper:.3f})",
            f"Recommendation: {recommendation.upper()}",
        ]

        return ORScoreCard(
            suggestion_id=suggestion.id,
            overall_score=round(overall, 4),
            approve_score=round(approve_score, 4),
            amend_score=round(amend_score, 4),
            reject_score=round(reject_score, 4),
            criteria_breakdown={k.value: round(v, 4) for k, v in criteria.items()},
            recommendation=recommendation,
            confidence_interval=(round(lower, 4), round(upper, 4)),
            reasoning=reasoning,
        )

    def _sensitivity_analysis(self, criteria: dict[CriteriaWeight, float]) -> tuple[float, float]:
        base = sum(criteria.get(c, 0) * w for c, w in self.AHP_WEIGHTS.items())
        min_val = max_val = base

        for crit in self.AHP_WEIGHTS:
            new_w = dict(self.AHP_WEIGHTS)
            increase = new_w[crit] * self.sensitivity_variance
            new_w[crit] += increase
            others = [c for c in new_w if c != crit]
            total_others = sum(new_w[c] for c in others)
            if total_others > 0:
                for c in others:
                    new_w[c] -= increase * (new_w[c] / total_others)
            score = sum(criteria.get(c, 0) * w for c, w in new_w.items())
            min_val = min(min_val, score)
            max_val = max(max_val, score)

        return min_val, max_val

    async def evaluate_batch(
        self, suggestions: list[AISuggestedTransaction],
        neural_map: dict[int, list[dict]] | None = None,
        extracted_map: dict[int, dict] | None = None,
    ) -> list[ORScoreCard]:
        neural_map = neural_map or {}
        extracted_map = extracted_map or {}
        cards = []
        for sug in suggestions:
            card = await self.evaluate(
                sug,
                neural_map.get(sug.id, []),
                extracted_map.get(sug.document_id, {}),
            )
            cards.append(card)
        cards.sort(key=lambda x: x.overall_score, reverse=True)
        return cards

    async def evaluate_suggestion_id(self, suggestion_id: int) -> ORScoreCard:
        sug = await self.db.get(AISuggestedTransaction, suggestion_id)
        if not sug:
            raise ValueError(f"Suggestion {suggestion_id} not found")
        return await self.evaluate(sug)

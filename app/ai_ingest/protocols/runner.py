"""
Protocol Runner — Incentive House ERP
Orchestrates Gate 1 (Agent) → Gate 2 (OR Evaluation) → Gate 3 (Surgery).
"""
import logging
from dataclasses import asdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_ingest.protocols.agent_protocol import (
    AIAgentProtocol, HallucinationError, IncitationError, OmissionError,
)
from app.ai_ingest.protocols.or_evaluation import OREvaluationProtocol
from app.ai_ingest.protocols.surgery_protocol import SurgeryProtocol, surgical_post_transaction
from app.ai_ingest.models import AISuggestedTransaction

logger = logging.getLogger(__name__)


class ProtocolRunner:

    def __init__(self, db: AsyncSession, performed_by: int = 0):
        self.db = db
        self.performed_by = performed_by
        self.agent = AIAgentProtocol(db)
        self.or_eval = OREvaluationProtocol(db)

    async def run_full_pipeline(
        self, doc_id: int, use_openai: bool = False, api_key: str | None = None,
    ) -> dict:
        result: dict[str, Any] = {
            "document_id": doc_id,
            "gate_1_agent": {},
            "gate_2_or": {},
            "gate_3_surgery": None,
            "final_status": "pending",
            "errors": [],
            "audit_trail": [],
            "suggestion_id": None,
        }

        # ===== GATE 1: AI AGENT PROTOCOL =====
        try:
            agent_result = await self.agent.execute(doc_id, use_openai=use_openai, api_key=api_key)
            if not agent_result["success"]:
                result["gate_1_agent"] = {"status": "failed", "error": agent_result.get("error")}
                result["final_status"] = "agent_failed"
                result["errors"].append(f"Gate 1: {agent_result.get('error', 'unknown error')}")
                return result

            ar = agent_result.get("agent_response", {})
            result["gate_1_agent"] = {
                "status": "passed",
                "vendor_source": ar.get("vendor_source"),
                "amount_source": ar.get("amount_source"),
                "confidence_score": agent_result.get("suggestion", {}).get("confidence_score", 0),
                "requires_human_review": ar.get("requires_human_review", False),
                "warnings": ar.get("warnings", []),
            }
        except (HallucinationError, IncitationError, OmissionError) as e:
            result["gate_1_agent"] = {"status": "blocked", "error": str(e)}
            result["final_status"] = "rejected_by_agent_protocol"
            result["errors"].append(f"Gate 1: {str(e)}")
            return result
        except Exception as e:
            result["gate_1_agent"] = {"status": "error", "error": str(e)}
            result["errors"].append(f"Gate 1 unexpected: {str(e)}")
            return result

        suggestion_id = agent_result.get("suggestion", {}).get("id")
        if not suggestion_id:
            result["final_status"] = "no_suggestion"
            result["errors"].append("Gate 1: No suggestion generated")
            return result

        result["suggestion_id"] = suggestion_id

        # ===== GATE 2: OR EVALUATION PROTOCOL =====
        try:
            sug = await self.db.get(AISuggestedTransaction, suggestion_id)
            if not sug:
                raise ValueError(f"Suggestion {suggestion_id} not found")

            analysis_data = agent_result.get("analysis", {})
            extracted_entities = (analysis_data.get("entities") or {}) if analysis_data else {}

            score_card = await self.or_eval.evaluate(
                sug,
                neural_matches=agent_result.get("suggestion", {}).get("neural_matches"),
                extracted_entities=extracted_entities,
            )

            result["gate_2_or"] = {
                "status": "scored",
                "overall_score": score_card.overall_score,
                "recommendation": score_card.recommendation,
                "confidence_interval": score_card.confidence_interval,
                "criteria_breakdown": score_card.criteria_breakdown,
                "reasoning": score_card.reasoning,
            }

            if score_card.recommendation == "reject":
                sug.status = "rejected"
                await self.db.commit()
                result["final_status"] = "rejected_by_or_protocol"
                result["errors"].append(
                    f"Gate 2: Score {score_card.overall_score:.3f} — REJECTED"
                )
                return result

            if score_card.recommendation in ("amend", "human_review"):
                result["gate_2_or"]["requires_human_review"] = True

        except Exception as e:
            result["gate_2_or"] = {"status": "error", "error": str(e)}
            result["errors"].append(f"Gate 2: {str(e)}")
            return result

        result["final_status"] = "awaiting_user_decision"
        result["audit_trail"] = [
            {"gate": 1, "protocol": "AI Agent", "status": "passed"},
            {"gate": 2, "protocol": "OR Evaluation", "status": "scored",
             "recommendation": result["gate_2_or"]["recommendation"]},
        ]
        return result

    async def execute_approved_suggestion(
        self, suggestion_id: int, user_id: int,
        amended: bool = False,
        amendment_data: dict | None = None,
    ) -> dict:
        sug = await self.db.get(AISuggestedTransaction, suggestion_id)
        if not sug:
            return {"success": False, "error": "Suggestion not found"}

        if amended and amendment_data:
            sug.review_notes = amendment_data.get("amended_description", sug.review_notes)
            await self.db.commit()

        try:
            surgery_result = await surgical_post_transaction(
                self.db, sug, user_id, amended=amended
            )
            return {
                "success": True,
                "gate_3_surgery": surgery_result,
                "final_status": "posted",
                "audit_trail": surgery_result["audit_trail"],
            }
        except Exception as e:
            return {
                "success": False,
                "gate_3_surgery": {"error": str(e)},
                "final_status": "surgery_failed",
                "errors": [f"Gate 3: {str(e)}"],
            }

    async def run_agent_only(self, doc_id: int) -> dict:
        try:
            agent_result = await self.agent.execute(doc_id)
            if agent_result["success"]:
                return {"status": "analyzed", "message": "Agent analysis completed", "results": agent_result}
            return {"status": "agent_failed", "message": agent_result.get("error", ""), "results": agent_result}
        except (HallucinationError, IncitationError, OmissionError) as e:
            return {"status": "rejected_by_agent", "message": str(e), "results": None}

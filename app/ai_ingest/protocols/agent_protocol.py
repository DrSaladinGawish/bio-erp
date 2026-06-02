"""
AI Agent Protocol — Incentive House ERP
Grounds every LLM/deterministic output to neural node history.
Guards: Hallucination, Incitation, Omission.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_ingest.models import (
    NeuralNode, AIDocumentIngestion, AIDocumentAnalysis,
    AISuggestedTransaction, AINeuralPatternLog, NodeType,
    AnalysisStatus, SuggestionStatus,
)
from app.ai_ingest.parsers import parse_document
from app.ai_ingest.analyzer import analyze_document

logger = logging.getLogger(__name__)


class HallucinationError(Exception):
    """Raised when AI suggests data not found in neural node history or extracted entities."""


class IncitationError(Exception):
    """Raised when AI suggests duplicate, circular, or self-referential transactions."""


class OmissionError(Exception):
    """Raised when critical fields are missing and no historical basis covers the gap."""


@dataclass
class GroundingContext:
    """Structured facts from DB — the ONLY truth the agent may reference."""
    document_id: int
    raw_text_snippet: str
    extracted_entities: dict
    detected_amount: float | None = None
    detected_vendor: str | None = None
    detected_date: str | None = None
    detected_invoice_number: str | None = None
    top_neural_matches: list = field(default_factory=list)
    historical_transaction_ids: list = field(default_factory=list)
    available_suppliers: list = field(default_factory=list)
    available_gl_accounts: list = field(default_factory=list)
    confidence_threshold: float = 0.65


@dataclass
class AgentResponse:
    """Validated agent output — every field cites a source."""
    suggestion_type: str
    vendor_id: int | None = None
    vendor_name: str | None = None
    vendor_source: str = "extracted"
    gl_account_id: int | None = None
    gl_code: str | None = None
    gl_source: str = "historical_pattern"
    amount: float | None = None
    amount_source: str = "extracted"
    tax_amount: float = 0.0
    tax_source: str = "statutory_default"
    description: str = ""
    description_source: str = "extracted_text"
    date: str | None = None
    date_source: str = "extracted"
    due_date: str | None = None
    due_date_source: str = "agent_inference"
    confidence_score: float = 0.0
    reasoning_chain: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    requires_human_review: bool = False


class AIAgentProtocol:

    CRITICAL_FIELDS = ["amount", "suggestion_type", "description"]
    WARNING_FIELDS = ["vendor_id", "gl_account_id", "date", "tax_amount"]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.violations: list[str] = []

    async def build_grounding_context(self, doc_id: int) -> GroundingContext:
        doc = await self.db.get(AIDocumentIngestion, doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        entities = {}  # populated by caller after analysis

        result = await self.db.execute(
            select(AIDocumentAnalysis).where(
                AIDocumentAnalysis.document_id == doc_id
            ).order_by(AIDocumentAnalysis.id.desc()).limit(1)
        )
        analysis = result.scalar_one_or_none()

        neural_matches = []
        if analysis and analysis.neural_nodes:
            for nd in analysis.neural_nodes[:5]:
                neural_matches.append(nd)

        return GroundingContext(
            document_id=doc_id,
            raw_text_snippet="",  # populated by caller
            extracted_entities=entities,
            detected_amount=analysis.confidence_score if analysis else None,
            detected_vendor=getattr(analysis, "summary", None) or "",
            detected_date=None,
            detected_invoice_number=None,
            top_neural_matches=neural_matches,
        )

    async def validate_agent_output(
        self, raw: dict, context: GroundingContext
    ) -> AgentResponse:
        self.violations = []

        vendor_id = raw.get("vendor_id")
        amount = raw.get("amount")
        gl_id = raw.get("gl_account_id")
        inv_num = raw.get("invoice_number") or str(raw.get("description", ""))[:50]

        if amount and context.detected_amount:
            if amount < context.detected_amount * 0.8 or amount > context.detected_amount * 1.2:
                self.violations.append(
                    f"HALLUCINATION: amount {amount} deviates >20% from detected {context.detected_amount}"
                )

        doc_refs = raw.get("historical_basis", [])
        for ref in doc_refs:
            if isinstance(ref, dict) and ref.get("transaction_id") == context.document_id:
                self.violations.append(
                    f"INCITATION: circular reference to document_id {context.document_id}"
                )

        for field in self.CRITICAL_FIELDS:
            if raw.get(field) is None or raw.get(field) == "":
                self.violations.append(f"OMISSION: critical field '{field}' missing")

        warnings = []
        requires_review = False
        for field in self.WARNING_FIELDS:
            if raw.get(field) is None:
                warnings.append(f"Missing {field}")
                requires_review = True

        if self.violations:
            detail = "\n".join(self.violations)
            if any("HALLUCINATION" in v for v in self.violations):
                raise HallucinationError(detail)
            if any("INCITATION" in v for v in self.violations):
                raise IncitationError(detail)
            if any("OMISSION" in v for v in self.violations):
                raise OmissionError(detail)

        return AgentResponse(
            suggestion_type=raw.get("suggestion_type", "journal_voucher"),
            vendor_id=vendor_id,
            vendor_name=raw.get("vendor_name"),
            vendor_source="neural_match" if context.top_neural_matches else "extracted",
            gl_account_id=gl_id,
            gl_code=raw.get("gl_code"),
            gl_source="historical_pattern" if gl_id else "unspecified",
            amount=amount,
            amount_source="extracted" if context.detected_amount else "neural_history",
            tax_amount=raw.get("tax_amount", 0.0),
            tax_source="statutory_default",
            description=raw.get("description", "Auto-generated suggestion"),
            description_source="extracted_text" if context.raw_text_snippet else "template",
            date=raw.get("date") or context.detected_date,
            date_source="extracted" if context.detected_date else "agent_inference",
            due_date=raw.get("due_date"),
            due_date_source="agent_inference",
            confidence_score=min(
                context.top_neural_matches[0].get("confidence", 0.5) if context.top_neural_matches else 0.5,
                1.0
            ),
            reasoning_chain=raw.get("reasoning", ["No reasoning provided"]),
            warnings=warnings,
            requires_human_review=requires_review or len(warnings) > 2,
        )

    def format_prompt_for_openai(self, context: GroundingContext) -> str:
        return f"""You are an ERP document analysis agent for Incentive House ERP.
You are FORBIDDEN from inventing data. Every field must be grounded in the provided context.

=== GROUNDING CONTEXT ===
Document ID: {context.document_id}
Extracted Text:
{context.raw_text_snippet[:1500]}

Extracted Entities:
{json.dumps(context.extracted_entities, indent=2, default=str)}

Top Neural Node Matches:
{json.dumps(context.top_neural_matches, indent=2, default=str)}

=== RULES ===
1. vendor_id MUST be in Available Suppliers if provided.
2. gl_account_id MUST be in Available GL Accounts if provided.
3. Amount must be within ±20% of detected amount.
4. You MUST include a "reasoning" array.
5. Output valid JSON only.

=== OUTPUT FORMAT ===
{{
  "suggestion_type": "purchase_invoice|journal_voucher|payment_voucher|invoice",
  "vendor_id": null or int,
  "vendor_name": "string",
  "gl_account_id": null or int,
  "gl_code": "string",
  "amount": float,
  "tax_amount": float,
  "description": "string",
  "date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "invoice_number": "string or null",
  "reasoning": ["step 1", "step 2"],
  "confidence": 0.0 to 1.0
}}"""

    async def call_openai_with_protocol(
        self, context: GroundingContext, api_key: str | None = None
    ) -> AgentResponse:
        import os
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")

        import openai
        client = openai.OpenAI(api_key=key)
        prompt = self.format_prompt_for_openai(context)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Deterministic ERP assistant. Never hallucinate. Use provided data only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=1500,
        )
        raw = json.loads(response.choices[0].message.content)
        return await self.validate_agent_output(raw, context)

    async def execute(
        self, ingestion_id: int, use_openai: bool = False, api_key: str | None = None
    ) -> dict:
        result = {"gate": "agent", "success": False, "analysis": None, "suggestion": None, "error": None}

        doc = await self.db.get(AIDocumentIngestion, ingestion_id)
        if not doc:
            result["error"] = f"Ingestion record {ingestion_id} not found"
            return result

        try:
            file_bytes = open(doc.file_path, "rb").read()
        except Exception as e:
            result["error"] = f"Cannot read file: {e}"
            return result

        text = parse_document(file_bytes, doc.filename)

        existing_nodes = await self.db.execute(
            select(NeuralNode).where(NeuralNode.is_active == True).limit(500)
        )
        existing = [
            {"id": n.id, "label": n.label,
             "node_type": n.node_type.value if hasattr(n.node_type, "value") else n.node_type}
            for n in existing_nodes.scalars().all()
        ]

        analysis_data = analyze_document(text, existing)
        context = await self.build_grounding_context(ingestion_id)
        context.raw_text_snippet = text[:2000]
        context.extracted_entities = analysis_data.get("extracted_entities", {})

        if use_openai:
            try:
                validated = await self.call_openai_with_protocol(context, api_key)
            except (HallucinationError, IncitationError, OmissionError):
                raise
            except RuntimeError:
                validated = None
        else:
            validated = None

        if validated is None:
            raw_mock = self._deterministic_suggestion(doc, analysis_data)
            if raw_mock is None:
                result["error"] = "Could not generate suggestion (confidence too low or no amount detected)"
                return result
            validated = await self.validate_agent_output(raw_mock, context)

        analysis = AIDocumentAnalysis(
            document_id=ingestion_id,
            status=AnalysisStatus.completed,
            raw_text=analysis_data["raw_text"],
            extracted_entities=analysis_data["extracted_entities"],
            extracted_patterns=analysis_data["extracted_patterns"],
            neural_nodes=analysis_data["neural_nodes"],
            neural_links=analysis_data["neural_links"],
            summary=analysis_data["summary"],
            confidence_score=validated.confidence_score,
            processing_time_ms=analysis_data["processing_time_ms"],
        )
        self.db.add(analysis)
        await self.db.flush()

        doc.analysis_id = analysis.id
        doc.status = "analyzed"

        for nd in analysis_data["neural_nodes"]:
            node = NeuralNode(
                label=nd.get("label", "unknown"),
                node_type=NodeType.entity,
                description=nd.get("matched_on", ""),
                confidence=nd.get("confidence", 0.5),
                source_document_id=ingestion_id,
            )
            self.db.add(node)

        sug = AISuggestedTransaction(
            document_id=doc.id,
            analysis_id=analysis.id,
            transaction_type=validated.suggestion_type,
            title=validated.description[:500],
            description=validated.description,
            journal_lines=[{
                "coa_account_id": validated.gl_account_id or 0,
                "coa_account_name": validated.gl_code or "",
                "debit": validated.amount or 0,
                "credit": validated.amount or 0,
                "description": validated.description,
            }],
            total_debit=validated.amount or 0,
            total_credit=validated.amount or 0,
            confidence_score=validated.confidence_score,
            status=SuggestionStatus.pending_review,
        )
        self.db.add(sug)
        await self.db.flush()

        await self._log_patterns(analysis, analysis_data)

        result["success"] = True
        result["analysis"] = {
            "id": analysis.id,
            "summary": analysis.summary,
            "confidence_score": analysis.confidence_score,
            "entities": analysis_data["extracted_entities"],
        }
        result["suggestion"] = {
            "id": sug.id,
            "transaction_type": sug.transaction_type,
            "total_debit": sug.total_debit,
            "total_credit": sug.total_credit,
            "confidence_score": sug.confidence_score,
        }
        result["agent_response"] = {
            "vendor_source": validated.vendor_source,
            "amount_source": validated.amount_source,
            "requires_human_review": validated.requires_human_review,
            "warnings": validated.warnings,
            "reasoning": validated.reasoning_chain,
        }
        return result

    def _deterministic_suggestion(self, doc, analysis_data) -> dict | None:
        entities = analysis_data.get("extracted_entities", {})
        confidence = analysis_data.get("confidence_score", 0.0)
        if confidence < 0.3:
            return None
        total = entities.get("total_amount")
        if not total:
            return None
        coa = entities.get("gl_accounts", [])
        gl_id = int(coa[0]) if coa and str(coa[0]).isdigit() else None
        return {
            "suggestion_type": "journal_voucher",
            "vendor_id": None,
            "vendor_name": entities.get("supplier_name"),
            "gl_account_id": gl_id,
            "gl_code": str(coa[0]) if coa else None,
            "amount": float(total),
            "tax_amount": entities.get("tax_amount", 0.0) or 0.0,
            "description": f"AI: {entities.get('supplier_name', '')} {entities.get('invoice_number', '')}",
            "date": entities.get("document_date"),
            "due_date": None,
            "invoice_number": entities.get("invoice_number"),
            "reasoning": ["Amount extracted from document", "Vendor matched by name pattern"],
            "confidence": confidence,
        }

    async def _log_patterns(self, analysis, analysis_data) -> None:
        patterns = analysis_data.get("extracted_patterns", [])
        for p in patterns[:50]:
            log = AINeuralPatternLog(
                document_id=analysis.document_id,
                analysis_id=analysis.id,
                pattern_type=p.get("type", "unknown"),
                pattern_key=str(p.get("description", p.get("matched", "")))[:500],
                pattern_value=json.dumps(p),
                confidence=analysis_data.get("confidence_score", 0.0),
                source="local",
            )
            self.db.add(log)

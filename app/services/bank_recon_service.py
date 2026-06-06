from __future__ import annotations

from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    BankStaging,
    BankImportSession,
    JVLine,
    JVHeader,
    RCTHeader,
    PMTHeader,
)


class BankReconService:
    """Auto-reconciliation matching engine for bank transactions."""

    @staticmethod
    async def auto_reconcile(
        db: AsyncSession,
        session_id: int,
        date_window_days: int = 3,
        amount_tolerance: float = 0.01,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(BankStaging).where(
                and_(
                    BankStaging.session_id == session_id,
                    BankStaging.is_matched == False,
                )
            )
        )
        staging_records = result.scalars().all()

        if not staging_records:
            return {
                "session_id": session_id,
                "total_unmatched": 0,
                "auto_matched": 0,
                "still_unmatched": 0,
                "matches": [],
            }

        gl_candidates: list[dict] = []

        jv_result = await db.execute(
            select(JVLine).options(joinedload(JVLine.jv))
        )
        for jv_line in jv_result.scalars().unique().all():
            gl_candidates.append({
                "source": "jv_line",
                "id": jv_line.id,
                "debit": jv_line.debit_amount,
                "credit": jv_line.credit_amount,
                "date": jv_line.jv.jv_date if jv_line.jv else None,
                "reference": jv_line.jv.reference if jv_line.jv else None,
                "description": jv_line.description,
            })

        rct_result = await db.execute(select(RCTHeader))
        for rct in rct_result.scalars().all():
            gl_candidates.append({
                "source": "receipt",
                "id": rct.id,
                "debit": 0.0,
                "credit": rct.amount,
                "date": rct.receipt_date,
                "reference": rct.bank_reference or rct.receipt_number,
                "description": rct.received_from or rct.notes,
            })

        pmt_result = await db.execute(select(PMTHeader))
        for pmt in pmt_result.scalars().all():
            gl_candidates.append({
                "source": "payment",
                "id": pmt.id,
                "debit": pmt.amount,
                "credit": 0.0,
                "date": pmt.payment_date,
                "reference": pmt.bank_reference or pmt.payment_number,
                "description": pmt.paid_to or pmt.notes,
            })

        matches = []
        matched_staging_ids: set[int] = set()
        matched_candidate_indices: set[int] = set()

        for staging in staging_records:
            if staging.id in matched_staging_ids:
                continue

            best_score = 0.0
            best_idx = -1
            best_candidate = None

            for i, candidate in enumerate(gl_candidates):
                if i in matched_candidate_indices:
                    continue

                score = BankReconService._score_match(
                    staging, candidate, date_window_days, amount_tolerance
                )
                if score > best_score:
                    best_score = score
                    best_idx = i
                    best_candidate = candidate

            if best_score >= 2.0 and best_candidate:
                staging.is_matched = True
                matched_staging_ids.add(staging.id)
                matched_candidate_indices.add(best_idx)
                matches.append({
                    "staging_id": staging.id,
                    "gl_source": best_candidate["source"],
                    "gl_id": best_candidate["id"],
                    "debit": best_candidate["debit"],
                    "credit": best_candidate["credit"],
                    "score": round(best_score, 1),
                })

        sess = await db.get(BankImportSession, session_id)
        if sess:
            sess.matched_count = (sess.matched_count or 0) + len(matches)
            sess.unmatched_count = max(0, len(staging_records) - len(matches))
            if sess.matched_count and sess.matched_count >= sess.total_transactions:
                sess.status = "MATCHED"
            elif sess.matched_count > 0:
                sess.status = "PARTIAL"

        await db.commit()

        return {
            "session_id": session_id,
            "total_unmatched": len(staging_records),
            "auto_matched": len(matches),
            "still_unmatched": len(staging_records) - len(matches),
            "matches": matches,
        }

    @staticmethod
    def _score_match(
        staging: BankStaging,
        candidate: dict,
        date_window_days: int,
        amount_tolerance: float,
    ) -> float:
        score = 0.0

        staging_amount = staging.debit_amount or staging.credit_amount
        candidate_amount = candidate["debit"] or candidate["credit"]

        if abs(staging_amount - candidate_amount) < amount_tolerance:
            score += 3.0
        elif abs(staging_amount - candidate_amount) <= 10.0:
            score += 2.0

        if staging.transaction_date and candidate.get("date"):
            date_diff = abs((staging.transaction_date - candidate["date"]).days)
            if date_diff == 0:
                score += 2.0
            elif date_diff <= date_window_days:
                score += 1.0

        if staging.reference and candidate.get("reference"):
            sref = staging.reference.lower()
            cref = candidate["reference"].lower()
            if sref == cref:
                score += 2.0
            elif sref in cref or cref in sref:
                score += 1.0

        if staging.description and candidate.get("description"):
            staging_words = set(staging.description.lower().split())
            candidate_words = set(candidate["description"].lower().split())
            common = staging_words.intersection(candidate_words)
            if len(common) >= 2:
                score += 1.0

        return score

    @staticmethod
    async def get_reconciliation_status(
        db: AsyncSession,
        session_id: int,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(BankStaging).where(BankStaging.session_id == session_id)
        )
        all_records = result.scalars().all()
        total = len(all_records)
        matched = sum(1 for r in all_records if r.is_matched)
        unmatched = total - matched

        return {
            "session_id": session_id,
            "total_transactions": total,
            "matched": matched,
            "unmatched": unmatched,
            "match_rate": round(matched / total * 100, 2) if total > 0 else 0,
        }

"""
Smart Reconciliation v2 — Co-Pilot Module C.
Fuzzy matching, auto-categorize, exception queue, and pattern learning.
"""

import json
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from .engine import CoPilotEngine
from .schemas import (
    ReconRequest, ReconResponse,
    Suggestion, ConfidenceLevel, Pattern,
)

COMMON_NARRATIONS = {
    "catering": ["catering", "cater", "food", "caterer", "buffet", "restaurant"],
    "av": ["av", "audio", "visual", "sound", "projector", "lighting", "production"],
    "decor": ["decor", "decoration", "floral", "flowers", "balloon", "centerpiece"],
    "venue": ["venue", "hall", "ballroom", "space", "rental", "banquet"],
    "entertainment": ["entertainment", "dj", "band", "performer", "music", "dance"],
    "transport": ["transport", "shuttle", "taxi", "car", "parking", "logistics"],
    "marketing": ["marketing", "print", "advertise", "promotion", "flyer", "social media"],
    "photography": ["photo", "photography", "videography", "camera", "video"],
    "security": ["security", "guard", "safety", "crowd control"],
}


class ReconAssistant:
    """
    Smart bank reconciliation with fuzzy matching, auto-categorization,
    pattern learning from user corrections.
    """

    def __init__(self, engine: CoPilotEngine):
        self.engine = engine
        self._cached_categories = self._build_category_embeddings()

    def _build_category_embeddings(self) -> Dict[str, Any]:
        result = {}
        for cat, keywords in COMMON_NARRATIONS.items():
            phrases = keywords + [cat]
            combined = " ".join(phrases)
            result[cat] = {"keywords": keywords, "text": combined}
        return result

    def reconcile_batch(self, request: ReconRequest) -> ReconResponse:
        matched = []
        unmatched = []
        suspicious = []
        suggestions = []

        for txn in request.transactions:
            result = self._reconcile_single(txn, request.auto_match_threshold)
            if result["status"] == "matched":
                matched.append(result)
            elif result["status"] == "suspicious":
                suspicious.append(result)
                suggestions.append(Suggestion(
                    id=f"suspicious_{txn.get('id','')}",
                    type="warning",
                    title=f"Suspicious: {txn.get('narration','')}",
                    description=f"Score: {result.get('score',0):.2f} — needs review",
                    confidence=self.engine.confidence(0.80),
                ))
            else:
                unmatched.append(result)

        if matched:
            suggestions.append(Suggestion(
                id="batch_auto_match", type="success",
                title=f"{len(matched)} transactions auto-matched",
                description=f"Confidence: {request.auto_match_threshold:.0%}+ threshold",
                action="apply",
                confidence=self.engine.confidence(0.95),
            ))

        stats = {
            "total": len(request.transactions),
            "matched": len(matched),
            "unmatched": len(unmatched),
            "suspicious": len(suspicious),
        }

        return ReconResponse(
            matched=matched, unmatched=unmatched, suspicious=suspicious,
            stats=stats, suggestions=suggestions,
            confidence=self.engine.confidence(0.92 if matched else 0.50),
        )

    def reconcile_single(self, bank_txn: Dict, system_txn: Optional[Dict] = None,
                         threshold: float = 0.85) -> Dict:
        return self._reconcile_single({"bank": bank_txn, "system": system_txn}, threshold)

    def _reconcile_single(self, txn_data: Dict, threshold: float) -> Dict:
        bank = txn_data.get("bank") or txn_data
        system = txn_data.get("system")

        amount = abs(float(bank.get("amount", bank.get("debit", 0)) or 0))
        narration = str(bank.get("narration", bank.get("description", "")))

        patterns = self.engine.find_matching_pattern("narration", narration)
        category = self._categorize_narration(narration)

        result = {
            "id": bank.get("id", bank.get("trnx_num", "")),
            "date": bank.get("date", ""),
            "amount": amount,
            "narration": narration,
            "category": category,
            "score": 0.0,
            "status": "unmatched",
            "suggested_match": None,
        }

        if system:
            amount_diff = abs(amount - abs(float(system.get("amount", 0))))
            date_match = bank.get("date", "")[:10] == system.get("date", "")[:10] if bank.get("date") and system.get("date") else False
            narration_sim = self.engine.similarity(narration, str(system.get("narration", system.get("description", ""))))

            score = 0.0
            if amount_diff == 0:
                score += 0.5
            if date_match:
                score += 0.2
            score += narration_sim * 0.3

            result["score"] = round(score, 4)
            result["suggested_match"] = system.get("id", "unknown")

            if score >= threshold:
                result["status"] = "matched"
            elif score >= threshold - 0.15:
                result["status"] = "suspicious"
        else:
            result["status"] = "unmatched"

        if patterns:
            result["pattern_match"] = patterns
            if result["score"] < threshold:
                result["score"] = max(result["score"], patterns.get("match_score", 0) * 0.8)
                if result["score"] >= threshold:
                    result["status"] = "matched"

        return result

    def _categorize_narration(self, narration: str) -> str:
        text = narration.lower()
        best_cat = "uncategorized"
        best_score = 0.0

        for cat, data in self._cached_categories.items():
            score = self.engine.similarity(text, data["text"])
            if score > best_score:
                best_score = score
                best_cat = cat

        for cat, data in self._cached_categories.items():
            for kw in data["keywords"]:
                if kw in text:
                    return cat

        return best_cat if best_score > 0.3 else "uncategorized"

    def learn_from_match(self, bank_txn: Dict, system_txn: Dict, correction: Optional[str] = None):
        narration = str(bank_txn.get("narration", ""))
        system_narration = str(system_txn.get("narration", ""))
        self.engine.learn_pattern("narration", narration, system_narration, {
            "bank_amount": bank_txn.get("amount"),
            "system_amount": system_txn.get("amount"),
            "correction": correction,
        })

    def get_learned_patterns(self) -> List[Dict]:
        return self.engine.get_all_patterns()

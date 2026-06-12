"""
CoPilotEngine — Local AI Core for IncentiveHouse ERP

Fully local inference using:
- OLMo 1B/7B via transformers (fallback to rule-based if model not loaded)
- sentence-transformers for semantic similarity
- scikit-learn for pattern classification
- Custom rule engine for business logic

NO cloud APIs. 100% offline.
"""

from __future__ import annotations
import os
import re
import json
import math
import hashlib
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("copilot.engine")

# ── Local AI Imports (with graceful fallbacks) ──────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False
    logger.warning("sentence-transformers not installed. Semantic search disabled.")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False
    logger.warning("scikit-learn not installed. ML matching disabled.")

try:
    import spacy
    _HAS_SPACY = True
except ImportError:
    _HAS_SPACY = False
    logger.warning("spaCy not installed. NLP features degraded.")

# OLMo optional — heavy model, loaded on demand
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False
    logger.warning("transformers not installed. LLM features disabled.")


# ── Enums & Dataclasses ─────────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    HIGH = "high"       # > 85%
    MEDIUM = "medium"   # 60-85%
    LOW = "low"         # 40-60%
    UNCERTAIN = "uncertain"  # < 40%


@dataclass
class Recommendation:
    """A single smart recommendation from the co-pilot."""
    id: str
    type: str                          # "template", "vendor", "budget", "staff", "action"
    title: str
    description: str
    confidence: ConfidenceLevel
    confidence_score: float            # 0.0 - 1.0
    data: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    action_label: str = "Apply"
    action_endpoint: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence.value,
            "confidence_score": round(self.confidence_score, 3),
            "data": self.data,
            "reason": self.reason,
            "action_label": self.action_label,
            "action_endpoint": self.action_endpoint,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PatternMatch:
    """Result of pattern matching against historical data."""
    pattern_name: str
    match_score: float
    matched_records: List[Dict[str, Any]]
    insights: List[str]


# ── CoPilotEngine ───────────────────────────────────────────────────────

class CoPilotEngine:
    """
    Central intelligence engine for IncentiveHouse ERP.

    Runs 100% locally using:
    - Rule-based business logic (always available)
    - Statistical pattern matching (scikit-learn)
    - Semantic similarity (sentence-transformers)
    - Local LLM inference (OLMo via transformers, optional)
    """

    # OLMo model identifiers
    OLMO_MODELS = {
        "1b": "allenai/OLMo-1B-hf",
        "7b": "allenai/OLMo-7B-hf",
    }

    def __init__(
        self,
        db_session_factory=None,
        olmo_model_size: Optional[str] = None,  # "1b", "7b", or None
        enable_embeddings: bool = True,
        cache_dir: str = "./.copilot_cache",
    ):
        self.db_session_factory = db_session_factory
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        # ── Local ML Models ─────────────────────────────────────────
        self._embedder: Optional[Any] = None
        self._olmo_model: Optional[Any] = None
        self._olmo_tokenizer: Optional[Any] = None
        self._nlp: Optional[Any] = None

        # Initialize embeddings (lightweight, ~80MB)
        if enable_embeddings and _HAS_SENTENCE_TRANSFORMERS:
            try:
                self._embedder = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    cache_folder=os.path.join(cache_dir, "embeddings"),
                )
                logger.info("✅ SentenceTransformer loaded (local)")
            except Exception as e:
                logger.warning(f"Failed to load embedder: {e}")

        # Initialize spaCy (lightweight, ~50MB)
        if _HAS_SPACY:
            try:
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("✅ spaCy loaded (local)")
            except OSError:
                logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")

        # Initialize OLMo (heavy, loaded on first use)
        self._olmo_size = olmo_model_size
        self._olmo_loaded = False

        # ── Business Rules Engine ────────────────────────────────────
        self._rules: List[Dict[str, Any]] = []
        self._load_default_rules()

        # ── Pattern Cache ────────────────────────────────────────────
        self._pattern_cache: Dict[str, Any] = {}

    # ═══════════════════════════════════════════════════════════════
    # OLMo Local LLM Interface
    # ═══════════════════════════════════════════════════════════════

    def _load_olmo(self) -> bool:
        """Lazy-load OLMo model. Returns True if successful."""
        if self._olmo_loaded:
            return True
        if not _HAS_TRANSFORMERS or not self._olmo_size:
            return False

        model_name = self.OLMO_MODELS.get(self._olmo_size)
        if not model_name:
            return False

        try:
            logger.info(f"🧠 Loading OLMo {self._olmo_size}... (first time, may take 2-5 min)")
            self._olmo_tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=os.path.join(self.cache_dir, "olmo"),
            )
            self._olmo_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                cache_dir=os.path.join(self.cache_dir, "olmo"),
                torch_dtype="auto",
                device_map="auto",
            )
            self._olmo_loaded = True
            logger.info(f"✅ OLMo {self._olmo_size} loaded successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load OLMo: {e}")
            return False

    def olmo_generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        Generate text using local OLMo model.
        Falls back to rule-based response if OLMo unavailable.
        """
        if not self._load_olmo():
            return self._rule_based_response(prompt)

        try:
            inputs = self._olmo_tokenizer(prompt, return_tensors="pt")
            outputs = self._olmo_model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self._olmo_tokenizer.eos_token_id,
            )
            response = self._olmo_tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"OLMo generation failed: {e}")
            return self._rule_based_response(prompt)

    def _rule_based_response(self, prompt: str) -> str:
        """Fallback response when OLMo is unavailable. Uses keyword matching."""
        prompt_lower = prompt.lower()

        if "budget" in prompt_lower:
            return "Based on historical data, I recommend setting a budget with 15% contingency."
        if "vendor" in prompt_lower or "supplier" in prompt_lower:
            return "Consider vendors with highest on-time delivery and quality ratings from past events."
        if "staff" in prompt_lower:
            return "Auto-assign staff based on event type, availability, and past performance ratings."
        if "reconcile" in prompt_lower or "bank" in prompt_lower:
            return "Use fuzzy matching with 85% confidence threshold for automatic reconciliation."
        return "I recommend reviewing historical patterns and applying business rules for optimal results."

    # ═══════════════════════════════════════════════════════════════
    # Semantic Similarity (Local Embeddings)
    # ═══════════════════════════════════════════════════════════════

    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using local embeddings. Returns 0.0-1.0."""
        if self._embedder is None:
            # Fallback: simple token overlap
            tokens1 = set(text1.lower().split())
            tokens2 = set(text2.lower().split())
            if not tokens1 or not tokens2:
                return 0.0
            return len(tokens1 & tokens2) / len(tokens1 | tokens2)

        try:
            embeddings = self._embedder.encode([text1, text2])
            sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(sim)
        except Exception as e:
            logger.warning(f"Embedding similarity failed: {e}")
            return 0.5

    def find_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> List[Tuple[int, float]]:
        """Find most similar candidates to query using local embeddings."""
        if not candidates:
            return []

        if self._embedder is None:
            # Fallback: TF-IDF + cosine via sklearn
            if _HAS_SKLEARN:
                vectorizer = TfidfVectorizer()
                try:
                    tfidf_matrix = vectorizer.fit_transform([query] + candidates)
                    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
                    results = [(i, float(similarities[i])) for i in range(len(candidates))]
                    results.sort(key=lambda x: x[1], reverse=True)
                    return [(i, s) for i, s in results if s >= threshold][:top_k]
                except Exception:
                    pass
            # Ultimate fallback: exact substring match
            return [(i, 1.0) for i, c in enumerate(candidates) if query.lower() in c.lower()][:top_k]

        try:
            query_emb = self._embedder.encode(query)
            cand_embs = self._embedder.encode(candidates)
            similarities = cosine_similarity([query_emb], cand_embs).flatten()
            results = [(i, float(similarities[i])) for i in range(len(candidates))]
            results.sort(key=lambda x: x[1], reverse=True)
            return [(i, s) for i, s in results if s >= threshold][:top_k]
        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════
    # Pattern Matching Engine
    # ═══════════════════════════════════════════════════════════════

    def _load_default_rules(self):
        """Load default business rules for IncentiveHouse ERP."""
        self._rules = [
            {
                "name": "high_value_event",
                "condition": lambda ctx: ctx.get("budget", 0) > 500_000,
                "action": lambda ctx: Recommendation(
                    id=self._gen_id(),
                    type="action",
                    title="High-Value Event Protocol",
                    description="Events over 500K EGP require executive approval and dual sign-off.",
                    confidence=ConfidenceLevel.HIGH,
                    confidence_score=0.95,
                    reason="Budget exceeds 500K threshold",
                    action_label="Initiate Approval Flow",
                    data={"threshold": 500_000, "current": ctx.get("budget")},
                ),
            },
            {
                "name": "repeat_client",
                "condition": lambda ctx: ctx.get("client_event_count", 0) > 5,
                "action": lambda ctx: Recommendation(
                    id=self._gen_id(),
                    type="template",
                    title=f"Repeat Client: {ctx.get('client_name', 'Unknown')}",
                    description=f"This client has {ctx.get('client_event_count')} past events. Use previous template?",
                    confidence=ConfidenceLevel.HIGH,
                    confidence_score=min(0.6 + ctx.get("client_event_count", 0) * 0.05, 0.98),
                    reason="High repeat client activity",
                    action_label="Load Last Template",
                    data={"last_event_id": ctx.get("last_event_id")},
                ),
            },
            {
                "name": "budget_variance_warning",
                "condition": lambda ctx: ctx.get("variance_pct", 0) > 15,
                "action": lambda ctx: Recommendation(
                    id=self._gen_id(),
                    type="budget",
                    title="Budget Variance Alert",
                    description=f"Current estimate is {ctx.get('variance_pct'):.1f}% over historical average.",
                    confidence=ConfidenceLevel.MEDIUM,
                    confidence_score=0.75,
                    reason="Variance exceeds 15%",
                    action_label="Review Budget",
                    data={"variance_pct": ctx.get("variance_pct"), "avg": ctx.get("historical_avg")},
                ),
            },
            {
                "name": "unpaid_invoices_warning",
                "condition": lambda ctx: ctx.get("unpaid_total", 0) > 100_000,
                "action": lambda ctx: Recommendation(
                    id=self._gen_id(),
                    type="action",
                    title="Outstanding Invoices Warning",
                    description=f"Client has {ctx.get('unpaid_count')} unpaid invoices totaling {ctx.get('unpaid_total'):,.0f} EGP.",
                    confidence=ConfidenceLevel.HIGH,
                    confidence_score=0.92,
                    reason="Outstanding balance > 100K EGP",
                    action_label="View Invoices",
                    data={"unpaid_total": ctx.get("unpaid_total"), "unpaid_count": ctx.get("unpaid_count")},
                ),
            },
            {
                "name": "supplier_delay_pattern",
                "condition": lambda ctx: ctx.get("supplier_delay_count", 0) >= 3,
                "action": lambda ctx: Recommendation(
                    id=self._gen_id(),
                    type="vendor",
                    title="Supplier Delay Alert",
                    description=f"{ctx.get('supplier_name')} has been delayed {ctx.get('supplier_delay_count')} times recently.",
                    confidence=ConfidenceLevel.HIGH,
                    confidence_score=0.88,
                    reason="Multiple delays detected",
                    action_label="Find Alternative",
                    data={"supplier_name": ctx.get("supplier_name"), "delay_count": ctx.get("supplier_delay_count")},
                ),
            },
        ]

    def evaluate_rules(self, context: Dict[str, Any]) -> List[Recommendation]:
        """Evaluate all business rules against context. Returns matching recommendations."""
        recommendations = []
        for rule in self._rules:
            try:
                if rule["condition"](context):
                    rec = rule["action"](context)
                    recommendations.append(rec)
            except Exception as e:
                logger.debug(f"Rule {rule['name']} failed: {e}")

        # Sort by confidence score descending
        recommendations.sort(key=lambda r: r.confidence_score, reverse=True)
        return recommendations

    # ═══════════════════════════════════════════════════════════════
    # NLP Utilities (Local)
    # ═══════════════════════════════════════════════════════════════

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities using local spaCy."""
        if self._nlp is None:
            # Fallback: regex-based extraction
            return self._regex_extract_entities(text)

        doc = self._nlp(text)
        entities = {"PERSON": [], "ORG": [], "MONEY": [], "DATE": [], "GPE": []}
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)
        return entities

    def _regex_extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Fallback entity extraction using regex."""
        entities = {"PERSON": [], "ORG": [], "MONEY": [], "DATE": [], "GPE": []}

        # Money patterns
        money_pattern = r'(?:EGP|USD|EUR|£|\$)\s*[\d,]+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?\s*(?:EGP|USD|EUR)'
        entities["MONEY"] = re.findall(money_pattern, text, re.IGNORECASE)

        # Date patterns
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}'
        entities["DATE"] = re.findall(date_pattern, text, re.IGNORECASE)

        return entities

    def classify_text(self, text: str, labels: List[str]) -> Dict[str, float]:
        """Classify text into labels using local embeddings + similarity."""
        if not labels:
            return {}

        similarities = {}
        for label in labels:
            sim = self.semantic_similarity(text, label)
            similarities[label] = sim

        # Normalize to probabilities (softmax)
        exp_scores = {k: math.exp(v * 5) for k, v in similarities.items()}  # temperature scaling
        total = sum(exp_scores.values())
        return {k: v / total for k, v in exp_scores.items()}

    # ═══════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _gen_id() -> str:
        """Generate unique recommendation ID."""
        return hashlib.md5(
            f"{datetime.now().isoformat()}{os.urandom(8)}".encode()
        ).hexdigest()[:12]

    @staticmethod
    def score_to_confidence(score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 0.85:
            return ConfidenceLevel.HIGH
        elif score >= 0.60:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.40:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNCERTAIN

    def cache_pattern(self, key: str, data: Any) -> None:
        """Cache computed pattern for reuse."""
        self._pattern_cache[key] = {
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    def get_cached_pattern(self, key: str, max_age_minutes: int = 30) -> Optional[Any]:
        """Retrieve cached pattern if not expired."""
        entry = self._pattern_cache.get(key)
        if not entry:
            return None

        age = datetime.now() - datetime.fromisoformat(entry["timestamp"])
        if age > timedelta(minutes=max_age_minutes):
            return None

        return entry["data"]


# ── Singleton Instance ──────────────────────────────────────────────────
_copilot_instance: Optional[CoPilotEngine] = None

def get_copilot_engine(
    db_session_factory=None,
    olmo_model_size: Optional[str] = None,
    enable_embeddings: bool = True,
) -> CoPilotEngine:
    """Get or create singleton CoPilotEngine instance."""
    global _copilot_instance
    if _copilot_instance is None:
        _copilot_instance = CoPilotEngine(
            db_session_factory=db_session_factory,
            olmo_model_size=olmo_model_size,
            enable_embeddings=enable_embeddings,
        )
    return _copilot_instance

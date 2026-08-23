"""
Co-Pilot Engine Core — Local AI inference layer.
Supports:
  - OLMo 1B/7B via transformers (if installed)
  - sentence-transformers for embeddings (lightweight, 80MB)
  - scikit-learn for pattern matching
  - Rule-based fallback when no LLM available
"""

import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Optional dependency detection ──────────────────────────────────────────

HAS_TORCH = False
HAS_TRANSFORMERS = False
HAS_SENTENCE = False
HAS_SKLEARN = False


def _check_torch():
    global HAS_TORCH
    if not HAS_TORCH:
        try:
            import torch  # noqa: F401
            HAS_TORCH = True
        except ImportError:
            pass


def _check_transformers():
    global HAS_TRANSFORMERS
    if not HAS_TRANSFORMERS:
        try:
            import transformers  # noqa: F401
            HAS_TRANSFORMERS = True
        except ImportError:
            pass


def _check_sentence():
    global HAS_SENTENCE
    if not HAS_SENTENCE:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            HAS_SENTENCE = True
        except ImportError:
            pass


def _check_sklearn():
    global HAS_SKLEARN
    if not HAS_SKLEARN:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
            from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401
            HAS_SKLEARN = True
        except ImportError:
            pass


class CoPilotEngine:
    """
    Core AI engine for IncentiveHouse Co-Pilot.
    Gracefully degrades from OLMo → embeddings → rule-based.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._embedder = None
        self._llm = None
        self._llm_tokenizer = None
        self._vectorizer = None
        self._patterns: Dict[str, List[Dict]] = {}
        self._learned_patterns: List[Dict] = []
        self._start_time = time.time()

        _check_torch()
        _check_transformers()
        _check_sentence()
        _check_sklearn()
        logger.info(f"CoPilotEngine init | torch={HAS_TORCH} transformers={HAS_TRANSFORMERS} "
                     f"sentence={HAS_SENTENCE} sklearn={HAS_SKLEARN}")

    # ── Embeddings ─────────────────────────────────────────────────────────

    def get_embedder(self):
        if self._embedder is None and HAS_SENTENCE:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence-transformers: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to load embedder: {e}")
        return self._embedder

    def embed(self, text: str) -> Optional[List[float]]:
        emb = self.get_embedder()
        if emb:
            return emb.encode(text, normalize_embeddings=True).tolist()
        return None

    # ── TF-IDF fallback ────────────────────────────────────────────────────

    def _get_vectorizer(self):
        if self._vectorizer is None and HAS_SKLEARN:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
        return self._vectorizer

    def _tfidf_similarity(self, a: str, b: str) -> float:
        vec = self._get_vectorizer()
        if vec is None:
            return 0.0
        try:
            tfidf = vec.fit_transform([a, b])
            from sklearn.metrics.pairwise import cosine_similarity
            sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return float(sim)
        except Exception:
            return 0.0

    # ── Text similarity (multi-strategy) ───────────────────────────────────

    def similarity(self, a: str, b: str) -> float:
        emb = self.embed(a)
        if emb:
            emb_b = self.embed(b)
            if emb_b:
                dot = sum(x * y for x, y in zip(emb, emb_b))
                return max(0.0, min(1.0, dot))
        return self._tfidf_similarity(a, b)

    def fuzzy_match(self, text: str, patterns: List[str], threshold: float = 0.7) -> List[Tuple[str, float]]:
        results = []
        for p in patterns:
            score = self.similarity(text, p)
            if score >= threshold:
                results.append((p, score))
        return sorted(results, key=lambda x: -x[1])

    # ── Pattern management (learned from user corrections) ─────────────────

    def learn_pattern(self, field: str, input_val: str, corrected_val: str, context: Optional[Dict] = None):
        if field not in self._patterns:
            self._patterns[field] = []
        self._patterns[field].append({
            "input": input_val,
            "corrected": corrected_val,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "occurrences": 1,
        })
        self._learned_patterns.append({
            "field": field, "input": input_val, "corrected": corrected_val,
            "timestamp": datetime.now().isoformat(),
        })
        logger.info(f"Learned pattern: {field} '{input_val}' -> '{corrected_val}'")

    def find_matching_pattern(self, field: str, value: str) -> Optional[Dict]:
        patterns = self._patterns.get(field, [])
        best = None
        best_score = 0.0
        for p in patterns:
            score = self.similarity(value, p["input"])
            if score > best_score:
                best_score = score
                best = p
        if best and best_score > 0.75:
            return {**best, "match_score": best_score}
        return None

    def get_all_patterns(self) -> List[Dict]:
        patterns = []
        for field, entries in self._patterns.items():
            for e in entries:
                patterns.append({"field": field, **e})
        return patterns

    def pattern_count(self) -> int:
        return len(self._learned_patterns)

    # ── Confidence scoring ─────────────────────────────────────────────────

    def confidence(self, score: float) -> Dict[str, Any]:
        if score >= 0.95:
            return {"score": score, "label": "very_high", "source": self._best_source()}
        elif score >= 0.85:
            return {"score": score, "label": "high", "source": self._best_source()}
        elif score >= 0.70:
            return {"score": score, "label": "medium", "source": self._best_source()}
        else:
            return {"score": score, "label": "low", "source": self._best_source()}

    def _best_source(self) -> str:
        if HAS_TRANSFORMERS and self._llm:
            return "local-llm"
        if HAS_SENTENCE and self._embedder:
            return "embeddings"
        if HAS_SKLEARN:
            return "tfidf"
        return "rule-based"

    # ── LLM inference (OLMo via transformers, optional) ────────────────────

    def load_llm(self, model_path: str = "allenai/OLMo-1B-hf"):
        if not HAS_TRANSFORMERS or not HAS_TORCH:
            logger.warning("Cannot load LLM: transformers/torch not installed")
            return False
        try:
            import transformers
            import torch
            self._llm_tokenizer = transformers.AutoTokenizer.from_pretrained(model_path)
            self._llm = transformers.AutoModelForCausalLM.from_pretrained(
                model_path, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            if torch.cuda.is_available():
                self._llm = self._llm.cuda()
            logger.info(f"Loaded OLMo model: {model_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load LLM: {e}")
            return False

    def ask_llm(self, prompt: str, max_tokens: int = 256) -> Optional[str]:
        if not self._llm or not self._llm_tokenizer:
            return None
        try:
            import torch
            inputs = self._llm_tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._llm.generate(
                    **inputs, max_new_tokens=max_tokens,
                    temperature=0.7, do_sample=True
                )
            return self._llm_tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            logger.error(f"LLM inference error: {e}")
            return None

    # ── Health ──────────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ready",
            "uptime_seconds": int(time.time() - self._start_time),
            "embedder_loaded": self._embedder is not None,
            "llm_loaded": self._llm is not None,
            "patterns_learned": self.pattern_count(),
            "torch": HAS_TORCH,
            "transformers": HAS_TRANSFORMERS,
            "sentence_transformers": HAS_SENTENCE,
            "sklearn": HAS_SKLEARN,
            "best_source": self._best_source(),
        }

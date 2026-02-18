"""Category classifier — lightweight scikit-learn model to label opportunity type."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline

from collector.core.config import settings
from collector.core.logging import get_logger
from collector.core.schemas import OpportunityCategory

log = get_logger(__name__)

# Default training data — a small seed set for bootstrapping.
# In production this would be replaced by a properly labeled dataset.
_SEED_DATA: list[tuple[str, str]] = [
    ("Road construction bridge repair highway paving", OpportunityCategory.CONSTRUCTION),
    ("Building renovation roofing plumbing electrical", OpportunityCategory.CONSTRUCTION),
    ("IT software development cloud migration cybersecurity", OpportunityCategory.IT_SERVICES),
    ("Network infrastructure server maintenance helpdesk", OpportunityCategory.IT_SERVICES),
    ("Legal advisory audit financial accounting", OpportunityCategory.PROFESSIONAL_SERVICES),
    ("Management consulting strategic planning", OpportunityCategory.CONSULTING),
    ("Office supplies furniture equipment purchase", OpportunityCategory.SUPPLIES),
    ("Medical equipment hospital supplies pharmaceuticals", OpportunityCategory.HEALTHCARE),
    ("Fleet management vehicle maintenance transit bus", OpportunityCategory.TRANSPORTATION),
    ("HVAC elevator janitorial facility maintenance", OpportunityCategory.MAINTENANCE),
]


class CategoryClassifier:
    """Train / load / predict opportunity categories."""

    def __init__(self, model_path: Path | None = None) -> None:
        """Initialise with an optional custom model path."""
        self.model_path = model_path or settings.classifier_model_path
        self.pipeline: Pipeline | None = None

    # ── training ──────────────────────────────────────────────────────────

    def train(self, texts: list[str] | None = None, labels: list[str] | None = None) -> None:
        """Train (or retrain) the classifier. Falls back to seed data if no args."""
        if texts is None or labels is None:
            texts = [t for t, _ in _SEED_DATA]
            labels = [label for _, label in _SEED_DATA]

        self.pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(stop_words="english", max_features=5_000)),
                ("clf", SGDClassifier(loss="modified_huber", random_state=42)),
            ]
        )
        self.pipeline.fit(texts, labels)
        log.info("classifier.trained", n_samples=len(texts))

    def save(self) -> None:
        """Persist the trained pipeline to disk."""
        assert self.pipeline is not None, "Train or load a model first."
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump(self.pipeline, f)
        log.info("classifier.saved", path=str(self.model_path))

    def load(self) -> None:
        """Load a previously saved pipeline, or train from seed data if missing."""
        if not self.model_path.exists():
            log.warning("classifier.model_not_found, training from seed", path=str(self.model_path))
            self.train()
            self.save()
            return
        with open(self.model_path, "rb") as f:
            self.pipeline = pickle.load(f)  # noqa: S301
        log.info("classifier.loaded", path=str(self.model_path))

    # ── prediction ────────────────────────────────────────────────────────

    def predict(self, text: str) -> tuple[OpportunityCategory, float]:
        """Return (category, confidence) for a single text."""
        if self.pipeline is None:
            self.load()
        assert self.pipeline is not None

        proba = self.pipeline.predict_proba([text])[0]
        idx = int(np.argmax(proba))
        label = self.pipeline.classes_[idx]
        confidence = float(proba[idx])

        try:
            category = OpportunityCategory(label)
        except ValueError:
            category = OpportunityCategory.OTHER

        return category, confidence

    def predict_batch(self, texts: list[str]) -> list[tuple[OpportunityCategory, float]]:
        """Batch prediction."""
        return [self.predict(t) for t in texts]

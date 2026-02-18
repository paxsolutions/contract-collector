"""End-to-end ML pipeline — normalize → classify → dedup → upsert canonical."""

from __future__ import annotations

from typing import Any

from collector.core.logging import get_logger
from collector.core.schemas import RawRecord
from collector.ml.classifier import CategoryClassifier
from collector.ml.dedup import find_duplicates
from collector.ml.normalizer import raw_to_canonical
from collector.storage.mongo import MongoStore

log = get_logger(__name__)


class ProcessingPipeline:
    """Runs normalization, classification, and dedup on raw records, then upserts canonical."""

    def __init__(self, store: MongoStore) -> None:
        """Initialise the pipeline with a MongoDB store and a category classifier."""
        self.store = store
        self.classifier = CategoryClassifier()

    async def run(self, batch_size: int = 200) -> dict[str, Any]:
        """Process all un-canonicalized raw records."""
        self.classifier.load()

        cursor = self.store.raw_collection.find().batch_size(batch_size)
        processed = 0
        upserted = 0

        raw_docs: list[dict[str, Any]] = []
        async for doc in cursor:
            raw_docs.append(doc)

        log.info("pipeline.start", total_raw=len(raw_docs))

        canonical_records = []
        for doc in raw_docs:
            raw = RawRecord(**{k: v for k, v in doc.items() if k != "_id"})
            canon = raw_to_canonical(raw)

            # Classify
            text = f"{canon.title} {canon.description}"
            category, confidence = self.classifier.predict(text)
            canon.category = category
            canon.category_confidence = confidence

            canonical_records.append(canon)
            processed += 1

        # Dedup detection (log only — doesn't auto-merge)
        canon_dicts = [c.model_dump() for c in canonical_records]
        dupes = find_duplicates(canon_dicts, threshold=0.85)
        if dupes:
            log.warning("pipeline.duplicates_detected", count=len(dupes))

        # Upsert canonical records
        for canon in canonical_records:
            written = await self.store.upsert_canonical(canon)
            if written:
                upserted += 1

        summary = {"processed": processed, "upserted": upserted, "duplicates_flagged": len(dupes)}
        log.info("pipeline.complete", **summary)
        return summary

"""MongoDB storage layer — raw + canonical collections with upsert/dedup logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

from collector.core.config import settings
from collector.core.logging import get_logger
from collector.core.schemas import CanonicalRecord, RawRecord

log = get_logger(__name__)


class MongoStore:
    """Async MongoDB wrapper that manages raw and canonical collections."""

    def __init__(self, uri: str | None = None, db_name: str | None = None) -> None:
        """Initialise the store with connection URI and database name."""
        self._uri = uri or str(settings.mongo_uri)
        self._db_name = db_name or settings.mongo_db
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the MongoDB connection and ensure indexes exist."""
        self._client = AsyncIOMotorClient(self._uri)
        self._db = self._client[self._db_name]
        await self._ensure_indexes()
        log.info("mongo.connected", db=self._db_name)

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            log.info("mongo.disconnected")

    async def _ensure_indexes(self) -> None:
        raw = self.raw_collection
        await raw.create_indexes(
            [
                IndexModel([("source_name", ASCENDING), ("source_id", ASCENDING)], unique=True),
                IndexModel([("content_hash", ASCENDING)]),
                IndexModel([("fetched_at", ASCENDING)]),
            ]
        )
        canon = self.canonical_collection
        await canon.create_indexes(
            [
                IndexModel([("record_id", ASCENDING)], unique=True),
                IndexModel([("source_name", ASCENDING), ("source_id", ASCENDING)]),
                IndexModel([("content_hash", ASCENDING)]),
                IndexModel([("category", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("due_date", ASCENDING)]),
            ]
        )

    # ── collection accessors ──────────────────────────────────────────────

    @property
    def raw_collection(self):  # type: ignore[override]
        """Return the raw records collection handle."""
        assert self._db is not None, "Call connect() first"
        return self._db[settings.raw_collection]

    @property
    def canonical_collection(self):  # type: ignore[override]
        """Return the canonical records collection handle."""
        assert self._db is not None, "Call connect() first"
        return self._db[settings.canonical_collection]

    # ── raw records ───────────────────────────────────────────────────────

    async def upsert_raw(self, record: RawRecord) -> bool:
        """Insert or skip raw record. Returns True if inserted (new)."""
        filt = {"source_name": record.source_name, "source_id": record.source_id}
        existing = await self.raw_collection.find_one(filt, {"content_hash": 1})
        if existing and existing.get("content_hash") == record.content_hash:
            log.debug("raw.skip_unchanged", source=record.source_name, id=record.source_id)
            return False
        await self.raw_collection.update_one(
            filt,
            {"$set": record.model_dump()},
            upsert=True,
        )
        log.info("raw.upserted", source=record.source_name, id=record.source_id)
        return True

    async def get_raw(self, source_name: str, source_id: str) -> dict[str, Any] | None:
        """Fetch a single raw record by source name and ID."""
        return await self.raw_collection.find_one(
            {"source_name": source_name, "source_id": source_id}
        )

    # ── canonical records ─────────────────────────────────────────────────

    async def upsert_canonical(self, record: CanonicalRecord) -> bool:
        """Upsert canonical record. Bumps version if content changed. Returns True if written."""
        filt = {"record_id": record.record_id}
        existing = await self.canonical_collection.find_one(filt, {"content_hash": 1, "version": 1})
        if existing and existing.get("content_hash") == record.content_hash:
            log.debug("canonical.skip_unchanged", record_id=record.record_id)
            return False

        new_version = (existing["version"] + 1) if existing else 1
        doc = record.model_dump()
        doc["version"] = new_version
        doc["updated_at"] = datetime.utcnow()

        await self.canonical_collection.update_one(filt, {"$set": doc}, upsert=True)
        log.info("canonical.upserted", record_id=record.record_id, version=new_version)
        return True

    async def find_canonical(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """Query canonical records with optional filter, skip, and limit."""
        cursor = self.canonical_collection.find(query or {}).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_canonical(self, query: dict[str, Any] | None = None) -> int:
        """Return the count of canonical records matching *query*."""
        return await self.canonical_collection.count_documents(query or {})

    # ── checkpoint helpers ────────────────────────────────────────────────

    async def get_latest_source_id(self, source_name: str) -> str | None:
        """Return the most-recently-fetched source_id for a given adapter (checkpointing)."""
        doc = await self.raw_collection.find_one(
            {"source_name": source_name},
            sort=[("fetched_at", -1)],
            projection={"source_id": 1},
        )
        return doc["source_id"] if doc else None

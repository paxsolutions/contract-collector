"""FastAPI application — serves procurement data for the dashboard."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from collector.core.logging import get_logger, setup_logging
from collector.storage.mongo import MongoStore

log = get_logger(__name__)

_store = MongoStore()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Open and close the MongoDB connection with the app lifecycle."""
    setup_logging()
    await _store.connect()
    log.info("api.startup")
    yield
    await _store.close()
    log.info("api.shutdown")


app = FastAPI(
    title="Contract Collector API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


# ── Summary stats ───────────────────────────────────────────────────────


@app.get("/api/stats")
async def stats() -> dict[str, Any]:
    """Return high-level counts and breakdowns."""
    raw_count = await _store.raw_collection.count_documents({})
    canonical_count = await _store.canonical_collection.count_documents({})

    # Category breakdown
    pipeline_cat = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    categories = [
        {"category": doc["_id"] or "uncategorized", "count": doc["count"]}
        async for doc in _store.canonical_collection.aggregate(pipeline_cat)
    ]

    # Source breakdown
    pipeline_src = [
        {"$group": {"_id": "$source_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    sources = [
        {"source": doc["_id"], "count": doc["count"]}
        async for doc in _store.raw_collection.aggregate(pipeline_src)
    ]

    # Status breakdown
    pipeline_status = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    statuses = [
        {"status": doc["_id"] or "unknown", "count": doc["count"]}
        async for doc in _store.canonical_collection.aggregate(pipeline_status)
    ]

    # Timeline (records per day)
    pipeline_timeline = [
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$fetched_at",
                    }
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
        {"$limit": 90},
    ]
    timeline = [
        {"date": doc["_id"], "count": doc["count"]}
        async for doc in _store.raw_collection.aggregate(pipeline_timeline)
    ]

    return {
        "raw_count": raw_count,
        "canonical_count": canonical_count,
        "categories": categories,
        "sources": sources,
        "statuses": statuses,
        "timeline": timeline,
    }


# ── Records listing ─────────────────────────────────────────────────────


@app.get("/api/records/raw")
async def list_raw(
    source: str | None = None,
    limit: int = Query(default=50, le=500),
    skip: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return paginated raw records with optional source filter."""
    query: dict[str, Any] = {}
    if source:
        query["source_name"] = source

    total = await _store.raw_collection.count_documents(query)
    cursor = (
        _store.raw_collection.find(query, {"_id": 0})
        .sort("fetched_at", -1)
        .skip(skip)
        .limit(limit)
    )
    records = [doc async for doc in cursor]

    return {"total": total, "records": records}


@app.get("/api/records/canonical")
async def list_canonical(
    source: str | None = None,
    category: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, le=500),
    skip: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return paginated canonical records with filters."""
    query: dict[str, Any] = {}
    if source:
        query["source_name"] = source
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"agency": {"$regex": search, "$options": "i"}},
        ]

    total = await _store.canonical_collection.count_documents(query)
    cursor = (
        _store.canonical_collection.find(query, {"_id": 0})
        .sort("posted_date", -1)
        .skip(skip)
        .limit(limit)
    )
    records = [doc async for doc in cursor]

    return {"total": total, "records": records}


# ── Sources list ────────────────────────────────────────────────────────


@app.get("/api/sources")
async def list_sources() -> list[dict[str, Any]]:
    """Return distinct source names with counts."""
    pipeline = [
        {"$group": {"_id": "$source_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    return [
        {"name": doc["_id"], "count": doc["count"]}
        async for doc in _store.raw_collection.aggregate(pipeline)
    ]

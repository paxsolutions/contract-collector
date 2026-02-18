"""Pydantic models — unified schema for procurement records."""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class OpportunityCategory(StrEnum):
    """Enumeration of procurement opportunity categories."""

    CONSTRUCTION = "construction"
    IT_SERVICES = "it_services"
    PROFESSIONAL_SERVICES = "professional_services"
    SUPPLIES = "supplies"
    CONSULTING = "consulting"
    HEALTHCARE = "healthcare"
    TRANSPORTATION = "transportation"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class OpportunityStatus(StrEnum):
    """Enumeration of procurement opportunity lifecycle statuses."""

    OPEN = "open"
    CLOSED = "closed"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class RawRecord(BaseModel):
    """Exactly what the scraper pulled — unmodified."""

    source_id: str = Field(..., description="ID assigned by the source portal")
    source_name: str = Field(..., description="Adapter / portal name")
    source_url: str = Field(..., description="URL the record was scraped from")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    raw_html: str | None = Field(default=None, description="HTML snapshot of the page")
    extracted: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs pulled by the adapter before normalization",
    )
    content_hash: str = Field(default="", description="SHA-256 of extracted dict for dedup")

    @model_validator(mode="after")
    def compute_content_hash(self) -> RawRecord:
        """Derive SHA-256 content hash from the extracted data if not already set."""
        if not self.content_hash:
            payload = str(sorted(self.extracted.items())).encode()
            self.content_hash = hashlib.sha256(payload).hexdigest()
        return self


class CanonicalRecord(BaseModel):
    """Normalized, deduplicated procurement opportunity."""

    record_id: str = Field(..., description="Deterministic ID: hash(source_name + source_id)")
    source_name: str
    source_id: str
    source_url: str

    title: str
    description: str = ""
    agency: str = ""
    posted_date: datetime | None = None
    due_date: datetime | None = None
    award_date: datetime | None = None
    estimated_value: float | None = None
    currency: str = "USD"

    status: OpportunityStatus = OpportunityStatus.UNKNOWN
    category: OpportunityCategory = OpportunityCategory.OTHER
    category_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    vendor_name: str | None = None
    vendor_normalized: str | None = None
    contact_info: str = ""
    location: str = ""

    tags: list[str] = Field(default_factory=list)
    content_hash: str = ""
    version: int = Field(default=1, description="Bumped on each upsert")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def compute_record_id(self) -> CanonicalRecord:
        """Derive deterministic record ID from source name and source ID."""
        if not self.record_id:
            payload = f"{self.source_name}:{self.source_id}".encode()
            self.record_id = hashlib.sha256(payload).hexdigest()
        return self

"""Data normalization — vendor names, dates, currency, addresses."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from collector.core.logging import get_logger
from collector.core.schemas import CanonicalRecord, OpportunityStatus, RawRecord

log = get_logger(__name__)

# Common suffixes / noise words to strip when normalizing vendor names
_VENDOR_NOISE = re.compile(
    r"\b(inc|llc|ltd|corp|corporation|company|co|group|holdings|plc|lp|llp)\b\.?",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")


def normalize_vendor_name(name: str | None) -> str | None:
    """Lowercase, strip legal suffixes, collapse whitespace."""
    if not name:
        return None
    cleaned = _VENDOR_NOISE.sub("", name)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip().lower()
    return cleaned or None


def parse_date(value: str | None) -> datetime | None:
    """Best-effort date parsing from common US/ISO formats."""
    if not value:
        return None
    value = value.strip()
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    log.debug("normalizer.date_parse_failed", value=value)
    return None


def parse_currency(value: str | None) -> tuple[float | None, str]:
    """Extract numeric amount and currency code from strings like '$1,234.56'."""
    if not value:
        return None, "USD"
    cleaned = re.sub(r"[^\d.\-]", "", value)
    try:
        amount = float(cleaned)
    except ValueError:
        return None, "USD"
    currency = "USD"  # default; extend with symbol detection if needed
    return amount, currency


def infer_status(extracted: dict[str, Any]) -> OpportunityStatus:
    """Heuristic status inference from extracted text fields."""
    text = " ".join(str(v) for v in extracted.values()).lower()
    if any(w in text for w in ("awarded", "award")):
        return OpportunityStatus.AWARDED
    if any(w in text for w in ("closed", "expired", "past due")):
        return OpportunityStatus.CLOSED
    if any(w in text for w in ("cancelled", "canceled")):
        return OpportunityStatus.CANCELLED
    if any(w in text for w in ("open", "active", "accepting")):
        return OpportunityStatus.OPEN
    return OpportunityStatus.UNKNOWN


def raw_to_canonical(raw: RawRecord) -> CanonicalRecord:
    """Transform a RawRecord into a CanonicalRecord with best-effort normalization."""
    ext = raw.extracted

    posted = parse_date(ext.get("posted_date") or ext.get("publish_date"))
    due = parse_date(ext.get("due_date") or ext.get("close_date") or ext.get("deadline"))
    award = parse_date(ext.get("award_date"))

    value_str = ext.get("estimated_value") or ext.get("amount") or ext.get("value")
    est_value, currency = parse_currency(value_str)

    vendor = ext.get("vendor") or ext.get("vendor_name") or ext.get("awardee")

    return CanonicalRecord(
        record_id="",  # auto-computed by model_validator
        source_name=raw.source_name,
        source_id=raw.source_id,
        source_url=raw.source_url,
        title=ext.get("title", ""),
        description=ext.get("description", ""),
        agency=ext.get("agency", ""),
        posted_date=posted,
        due_date=due,
        award_date=award,
        estimated_value=est_value,
        currency=currency,
        status=infer_status(ext),
        vendor_name=vendor,
        vendor_normalized=normalize_vendor_name(vendor),
        contact_info=ext.get("contact", ""),
        location=ext.get("location", ""),
        content_hash=raw.content_hash,
    )

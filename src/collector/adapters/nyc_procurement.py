"""Adapter for NYC procurement — via NYC Open Data (SODA API).

Uses the *Current Solicitations* dataset (``3khw-qi8f``) published by
the Office of Citywide Procurement on ``data.cityofnewyork.us``.
No API key or browser required.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from playwright.async_api import Page

from collector.adapters.base import AdapterMeta, BaseAdapter
from collector.adapters.registry import register_adapter
from collector.core.logging import get_logger
from collector.core.schemas import RawRecord

log = get_logger(__name__)

_SODA_BASE = "https://data.cityofnewyork.us/resource/3khw-qi8f.json"
_PAGE_SIZE = 50


@register_adapter
class NYCProcurementAdapter(BaseAdapter):
    """Fetch NYC solicitations from the Open Data SODA API."""

    meta = AdapterMeta(
        name="nyc_procurement",
        base_url="https://data.cityofnewyork.us",
        description="New York City current solicitations (Open Data)",
        tags=["city", "nyc", "us"],
        requires_browser=False,
    )

    async def extract(self, page: Page | None) -> AsyncIterator[RawRecord]:
        """Page through the NYC Open Data solicitations endpoint."""
        offset = 0

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                params = {
                    "$limit": _PAGE_SIZE,
                    "$offset": offset,
                    "$order": "start_date DESC",
                    "section_name": "Procurement",
                }
                log.info("nyc.api.request", offset=offset)
                resp = await client.get(_SODA_BASE, params=params)
                resp.raise_for_status()
                rows = resp.json()

                if not rows:
                    log.info("nyc.extract.no_more_results", offset=offset)
                    break

                for row in rows:
                    source_id = row.get("request_id", "") or row.get("pin", "")
                    if not source_id:
                        continue

                    if self.checkpoint and source_id == self.checkpoint:
                        log.info("nyc.extract.checkpoint_reached",
                                 source_id=source_id)
                        return

                    yield RawRecord(
                        source_id=source_id,
                        source_name=self.meta.name,
                        source_url=(
                            f"https://data.cityofnewyork.us/resource/3khw-qi8f/"
                            f"{source_id}"
                        ),
                        extracted={
                            "title": row.get("short_title", ""),
                            "agency": row.get("agency_name", ""),
                            "category": row.get("category_description", ""),
                            "notice_type": row.get("type_of_notice_description", ""),
                            "selection_method": row.get("selection_method_description", ""),
                            "pin": row.get("pin", ""),
                            "due_date": row.get("due_date", ""),
                            "posted_date": row.get("start_date", ""),
                            "contact_name": row.get("contact_name", ""),
                            "contact_email": row.get("email", ""),
                        },
                    )

                offset += _PAGE_SIZE

        log.info("nyc.extract.done")

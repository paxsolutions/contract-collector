"""Adapter for SAM.gov — the US federal procurement portal.

Uses the public ``api.sam.gov`` Opportunities REST API (v2).  Requires
a free API key obtainable from your SAM.gov Account Details page.
Set the key via ``COLLECTOR_SAM_GOV_API_KEY`` env var.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
from playwright.async_api import Page

from collector.adapters.base import AdapterMeta, BaseAdapter
from collector.adapters.registry import register_adapter
from collector.core.config import settings
from collector.core.logging import get_logger
from collector.core.schemas import RawRecord

log = get_logger(__name__)

_API_BASE = "https://api.sam.gov/opportunities/v2/search"
_PAGE_SIZE = 25


@register_adapter
class SamGovAdapter(BaseAdapter):
    """Fetch active federal contract opportunities from the SAM.gov API."""

    meta = AdapterMeta(
        name="sam_gov",
        base_url="https://api.sam.gov",
        description="US federal procurement opportunities (SAM.gov API)",
        tags=["federal", "us"],
        requires_browser=False,
    )

    async def extract(self, page: Page | None) -> AsyncIterator[RawRecord]:
        """Page through the SAM.gov Opportunities API and yield raw records."""
        api_key = getattr(settings, "sam_gov_api_key", "") or ""
        if not api_key:
            log.error("sam_gov.extract.missing_api_key",
                      hint="Set COLLECTOR_SAM_GOV_API_KEY in .env")
            return

        now = datetime.now(tz=UTC)
        posted_from = (now - timedelta(days=30)).strftime("%m/%d/%Y")
        posted_to = now.strftime("%m/%d/%Y")
        offset = 0

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                params = {
                    "api_key": api_key,
                    "postedFrom": posted_from,
                    "postedTo": posted_to,
                    "limit": _PAGE_SIZE,
                    "offset": offset,
                }
                log.info("sam_gov.api.request", offset=offset)
                resp = await client.get(_API_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()

                opps = data.get("opportunitiesData", [])
                if not opps:
                    log.info("sam_gov.extract.no_more_results", offset=offset)
                    break

                for opp in opps:
                    notice_id = opp.get("noticeId", "")
                    if self.checkpoint and notice_id == self.checkpoint:
                        log.info("sam_gov.extract.checkpoint_reached",
                                 source_id=notice_id)
                        return

                    yield RawRecord(
                        source_id=notice_id,
                        source_name=self.meta.name,
                        source_url=opp.get("uiLink", f"https://sam.gov/opp/{notice_id}/view"),
                        extracted={
                            "title": opp.get("title", ""),
                            "agency": opp.get("department", ""),
                            "sub_tier": opp.get("subTier", ""),
                            "office": opp.get("office", ""),
                            "posted_date": opp.get("postedDate", ""),
                            "response_deadline": opp.get("responseDeadLine", ""),
                            "type": opp.get("type", ""),
                            "set_aside": opp.get("typeOfSetAsideDescription", ""),
                            "naics_code": opp.get("naicsCode", ""),
                            "solicitation_number": opp.get("solicitationNumber", ""),
                        },
                    )

                total = data.get("totalRecords", 0)
                offset += _PAGE_SIZE
                if offset >= total:
                    break

        log.info("sam_gov.extract.done")

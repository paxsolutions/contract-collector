"""Adapter for NYC PASSPort — New York City's Procurement and Sourcing Solutions Portal.

NYC PASSPort is an AJAX-heavy portal with dynamic filtering and paginated
results tables.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from playwright.async_api import Page

from collector.adapters.base import AdapterMeta, BaseAdapter
from collector.adapters.registry import register_adapter
from collector.core.logging import get_logger
from collector.core.schemas import RawRecord

log = get_logger(__name__)


@register_adapter
class NYCProcurementAdapter(BaseAdapter):
    """Scraper for NYC PASSPort procurement opportunities."""

    meta = AdapterMeta(
        name="nyc_procurement",
        base_url="https://www.nyc.gov/site/mocs/opportunities/current-solicitations.page",
        description="New York City current solicitations",
        tags=["city", "nyc", "us"],
    )

    async def extract(self, page: Page) -> AsyncIterator[RawRecord]:
        """Yield procurement records from the NYC PASSPort solicitations page."""
        log.info("nyc.extract.start", url=page.url)

        # Wait for the solicitations table to render
        await page.wait_for_selector("table tbody tr, .solicitation-item", timeout=20_000)

        rows = await page.query_selector_all("table tbody tr, .solicitation-item")
        for row in rows:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 3:
                    continue

                title = (await cells[0].inner_text()).strip()
                agency = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
                due_date = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""

                link_el = await cells[0].query_selector("a")
                link = (await link_el.get_attribute("href")) if link_el else ""

                source_id = (link or "").split("/")[-1] or title[:40]

                if self.checkpoint and source_id == self.checkpoint:
                    log.info("nyc.extract.checkpoint_reached", source_id=source_id)
                    return

                yield RawRecord(
                    source_id=source_id,
                    source_name=self.meta.name,
                    source_url=link or page.url,
                    extracted={
                        "title": title,
                        "agency": agency,
                        "due_date": due_date,
                        "link": link,
                    },
                )
            except Exception:
                log.exception("nyc.extract.row_error")
                await self.save_snapshot(page, label="row_error")

        log.info("nyc.extract.done")

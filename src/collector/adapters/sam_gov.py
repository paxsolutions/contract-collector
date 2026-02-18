"""Adapter for SAM.gov — the US federal procurement portal.

SAM.gov exposes contract opportunities via a JS-heavy search interface.
This adapter navigates the opportunity search, handles pagination, and
extracts listing details.
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
class SamGovAdapter(BaseAdapter):
    """Scraper for SAM.gov contract opportunities."""

    meta = AdapterMeta(
        name="sam_gov",
        base_url="https://sam.gov/search/?index=opp&page=1&sort=-modifiedDate&sfm%5Bstatus%5D%5Bis_active%5D=true",
        description="US federal procurement opportunities (SAM.gov)",
        tags=["federal", "us"],
    )

    async def extract(self, page: Page) -> AsyncIterator[RawRecord]:
        """Navigate SAM.gov opportunity listing and yield raw records."""
        log.info("sam_gov.extract.start", url=page.url)

        while True:
            # Wait for the results table to load
            await page.wait_for_selector(
                "[data-testid='opportunity-result'], .opportunity-result, .results-list .result",
                timeout=15_000,
            )

            rows = await page.query_selector_all(
                "[data-testid='opportunity-result'], .opportunity-result, .results-list .result"
            )
            if not rows:
                log.info("sam_gov.extract.no_rows")
                break

            for row in rows:
                try:
                    title_el = await row.query_selector("h3 a, .title a, a.opportunity-link")
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    link = await title_el.get_attribute("href") if title_el else ""

                    agency_el = await row.query_selector(
                        ".agency, [data-testid='agency'], .department"
                    )
                    agency = (await agency_el.inner_text()).strip() if agency_el else ""

                    date_el = await row.query_selector(
                        ".date, [data-testid='posted-date'], .posted-date"
                    )
                    date_text = (await date_el.inner_text()).strip() if date_el else ""

                    source_id = (link or "").split("/")[-1] or title[:40]

                    # Check against checkpoint for incremental runs
                    if self.checkpoint and source_id == self.checkpoint:
                        log.info("sam_gov.extract.checkpoint_reached", source_id=source_id)
                        return

                    yield RawRecord(
                        source_id=source_id,
                        source_name=self.meta.name,
                        source_url=f"https://sam.gov{link}" if link else page.url,
                        extracted={
                            "title": title,
                            "agency": agency,
                            "posted_date": date_text,
                            "link": link,
                        },
                    )
                except Exception:
                    log.exception("sam_gov.extract.row_error")
                    await self.save_snapshot(page, label="row_error")

            # Pagination — try clicking next
            next_btn = await page.query_selector(
                "button[aria-label='Next'], .pagination .next:not(.disabled)"
            )
            if next_btn and await next_btn.is_enabled():
                await next_btn.click()
                await page.wait_for_load_state("networkidle")
            else:
                log.info("sam_gov.extract.last_page")
                break

        log.info("sam_gov.extract.done")

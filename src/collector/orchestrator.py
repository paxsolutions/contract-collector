"""Orchestrator — drives adapters with concurrency, rate-limiting, retries, and checkpointing."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from typing import Any

from aiolimiter import AsyncLimiter
from playwright.async_api import async_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from collector.adapters.registry import ADAPTER_REGISTRY, get_adapter
from collector.core.config import settings
from collector.core.logging import get_logger
from collector.storage.mongo import MongoStore

log = get_logger(__name__)


class CollectorMetrics:
    """Simple in-memory metrics for a single run."""

    def __init__(self) -> None:
        """Reset all counters to zero."""
        self.items_collected: int = 0
        self.items_skipped: int = 0
        self.failures: int = 0
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    @property
    def elapsed_s(self) -> float:
        """Wall-clock seconds elapsed during the run."""
        return self.end_time - self.start_time

    def summary(self) -> dict[str, Any]:
        """Return a dict summarising collected, skipped, failed counts and elapsed time."""
        return {
            "items_collected": self.items_collected,
            "items_skipped": self.items_skipped,
            "failures": self.failures,
            "elapsed_s": round(self.elapsed_s, 2),
        }


class Orchestrator:
    """Top-level runner that coordinates adapters, browser contexts, and storage."""

    def __init__(
        self,
        store: MongoStore,
        adapter_names: Sequence[str] | None = None,
    ) -> None:
        """Create an orchestrator bound to a store and optional adapter whitelist."""
        self.store = store
        self.adapter_names = adapter_names or list(ADAPTER_REGISTRY.keys())
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._domain_limiters: dict[str, AsyncLimiter] = {}
        self.metrics = CollectorMetrics()

    def _get_limiter(self, domain: str) -> AsyncLimiter:
        if domain not in self._domain_limiters:
            self._domain_limiters[domain] = AsyncLimiter(
                max_rate=settings.rate_limit_per_domain, time_period=1.0
            )
        return self._domain_limiters[domain]

    # ── public API ────────────────────────────────────────────────────────

    async def run(self) -> dict[str, Any]:
        """Execute collection for all configured adapters. Returns metrics summary."""
        self.metrics = CollectorMetrics()
        self.metrics.start_time = time.monotonic()

        async with async_playwright() as pw:
            browser = await pw[settings.browser_type].launch(headless=settings.headless)
            try:
                tasks = [
                    self._run_adapter(browser, name) for name in self.adapter_names
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                await browser.close()

        self.metrics.end_time = time.monotonic()
        summary = self.metrics.summary()
        log.info("orchestrator.run.complete", **summary)
        return summary

    # ── per-adapter execution ─────────────────────────────────────────────

    async def _run_adapter(self, browser: Any, adapter_name: str) -> None:
        async with self._semaphore:
            log.info("orchestrator.adapter.start", adapter=adapter_name)
            try:
                adapter_cls = get_adapter(adapter_name)

                # Checkpoint: resume from last-seen source_id
                checkpoint = await self.store.get_latest_source_id(adapter_name)
                adapter = adapter_cls(checkpoint=checkpoint)

                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()
                page.set_default_timeout(settings.request_timeout_s * 1000)

                start_url = adapter.build_start_url()

                await self._navigate_with_retry(page, start_url)
                await adapter.login(page)

                limiter = self._get_limiter(adapter.meta.base_url.split("/")[2])

                async for record in adapter.extract(page):
                    async with limiter:
                        inserted = await self.store.upsert_raw(record)
                        if inserted:
                            self.metrics.items_collected += 1
                        else:
                            self.metrics.items_skipped += 1

                await context.close()
                log.info("orchestrator.adapter.done", adapter=adapter_name)

            except Exception:
                self.metrics.failures += 1
                log.exception("orchestrator.adapter.failed", adapter=adapter_name)

    # ── retry-enabled navigation ──────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_backoff_base, min=1, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _navigate_with_retry(self, page: Any, url: str) -> None:
        log.debug("orchestrator.navigate", url=url)
        await page.goto(url, wait_until="domcontentloaded")

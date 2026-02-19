"""Base adapter interface — every source portal implements this."""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Page

from collector.core.config import settings
from collector.core.logging import get_logger
from collector.core.schemas import RawRecord

log = get_logger(__name__)


@dataclass
class AdapterMeta:
    """Metadata describing a source adapter."""

    name: str
    base_url: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    requires_browser: bool = True


class BaseAdapter(abc.ABC):
    """Abstract base for all procurement-portal adapters.

    Subclasses must implement:
      - ``meta`` (class attribute / property)
      - ``extract(page) -> AsyncIterator[RawRecord]``

    For API-only adapters set ``meta.requires_browser = False``;
    the orchestrator will pass ``page=None``.

    Optionally override:
      - ``login(page)`` for authenticated portals
      - ``build_start_url()`` if the start URL depends on checkpoint state
    """

    meta: AdapterMeta

    def __init__(self, checkpoint: str | None = None) -> None:
        """Initialise the adapter with an optional checkpoint for incremental runs."""
        self.checkpoint = checkpoint  # last-seen source_id for incremental runs

    # ── hooks ─────────────────────────────────────────────────────────────

    async def login(self, page: Page) -> None:  # noqa: ARG002, B027
        """Override for portals that require authentication."""

    def build_start_url(self) -> str:
        """Return the URL to begin scraping. Override for pagination/checkpointing."""
        return self.meta.base_url

    # ── core contract ─────────────────────────────────────────────────────

    @abc.abstractmethod
    async def extract(self, page: Page | None) -> AsyncIterator[RawRecord]:
        """Yield RawRecord instances from the portal.

        For browser adapters the orchestrator provides a Playwright ``Page``
        already navigated to ``build_start_url()``.  API adapters receive
        ``None`` and should use ``httpx`` or similar.
        """
        ...  # pragma: no cover
        # Make this an async generator so type checkers are happy
        yield  # type: ignore[misc]

    # ── snapshot helper ───────────────────────────────────────────────────

    async def save_snapshot(self, page: Page | None, label: str = "error") -> Path:
        """Save an HTML snapshot on failure for debugging."""
        if page is None:
            log.warning("snapshot.skipped", reason="no_page", adapter=self.meta.name)
            return Path("/dev/null")
        snap_dir = settings.snapshot_dir / self.meta.name
        snap_dir.mkdir(parents=True, exist_ok=True)
        path = snap_dir / f"{label}_{page.url.split('/')[-1][:60]}.html"
        content = await page.content()
        path.write_text(content, encoding="utf-8")
        log.warning("snapshot.saved", path=str(path), adapter=self.meta.name)
        return path

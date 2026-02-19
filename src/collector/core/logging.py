"""Structured logging — rich console for local dev, JSON for production."""

from __future__ import annotations

import logging
import sys

import structlog
from rich.console import Console
from rich.theme import Theme

from collector.core.config import settings

# ── Rich console with custom theme ─────────────────────────────────────

_THEME = Theme(
    {
        "log.level.debug": "dim cyan",
        "log.level.info": "bold green",
        "log.level.warning": "bold yellow",
        "log.level.error": "bold red",
        "log.level.critical": "bold white on red",
        "log.event": "bold white",
        "log.key": "dim",
        "log.value": "cyan",
    }
)

console = Console(stderr=True, theme=_THEME)


def setup_logging() -> None:
    """Configure structlog + stdlib logging for the entire application."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.log_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        _kv = structlog.dev.KeyValueColumnFormatter
        renderer = structlog.dev.ConsoleRenderer(
            columns=[
                structlog.dev.Column(
                    "timestamp",
                    _kv(
                        key_style=None, value_style="dim",
                        reset_style="dim", prefix="", postfix=" ",
                    ),
                ),
                structlog.dev.Column("level", structlog.dev.LogLevelColumnFormatter()),
                structlog.dev.Column(
                    "event",
                    _kv(key_style=None, value_style="bold", reset_style="", prefix="", postfix=" "),
                ),
                structlog.dev.Column(
                    "",
                    _kv(key_style="dim", value_style="cyan", reset_style="", prefix="", postfix=""),
                ),
            ],
            exception_formatter=structlog.dev.rich_traceback,
        )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger."""
    return structlog.get_logger(name)  # type: ignore[return-value]

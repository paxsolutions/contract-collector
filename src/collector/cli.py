"""CLI entry point — ``collector`` command."""

from __future__ import annotations

import asyncio
import json

import click

from collector.core.logging import get_logger, setup_logging

log = get_logger(__name__)


@click.group()
@click.option("--log-level", default=None, help="Override log level (DEBUG, INFO, WARNING, ERROR)")
def main(log_level: str | None) -> None:
    """Public Procurement & Contract Intelligence Collector."""
    if log_level:
        import collector.core.config as cfg
        cfg.settings.log_level = log_level
    setup_logging()


@main.command()
@click.option(
    "--adapters", "-a", multiple=True, default=None, help="Adapter names to run (default: all)"
)
def collect(adapters: tuple[str, ...]) -> None:
    """Run the scraping collector for configured adapters."""
    from collector.adapters import nyc_procurement, sam_gov  # noqa: F401 — register adapters
    from collector.orchestrator import Orchestrator
    from collector.storage import MongoStore

    async def _run() -> None:
        store = MongoStore()
        await store.connect()
        try:
            orch = Orchestrator(store, adapter_names=adapters or None)
            summary = await orch.run()
            click.echo(json.dumps(summary, indent=2))
        finally:
            await store.close()

    asyncio.run(_run())


@main.command()
@click.option("--batch-size", default=200, help="Records per batch")
def process(batch_size: int) -> None:
    """Run the ML processing pipeline (normalize → classify → dedup → upsert)."""
    from collector.ml.pipeline import ProcessingPipeline
    from collector.storage import MongoStore

    async def _run() -> None:
        store = MongoStore()
        await store.connect()
        try:
            pipeline = ProcessingPipeline(store)
            summary = await pipeline.run(batch_size=batch_size)
            click.echo(json.dumps(summary, indent=2))
        finally:
            await store.close()

    asyncio.run(_run())


@main.command()
def train_classifier() -> None:
    """Train the category classifier from seed data and save it."""
    from collector.ml.classifier import CategoryClassifier

    clf = CategoryClassifier()
    clf.train()
    clf.save()
    click.echo("Classifier trained and saved.")


@main.command()
def list_adapters() -> None:
    """List all registered adapters."""
    from collector.adapters import nyc_procurement, sam_gov  # noqa: F401
    from collector.adapters.registry import ADAPTER_REGISTRY

    for name, cls in sorted(ADAPTER_REGISTRY.items()):
        click.echo(f"  {name:25s} {cls.meta.description}")


if __name__ == "__main__":
    main()

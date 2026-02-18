"""Shared test fixtures."""

import pytest

from collector.core.logging import setup_logging


@pytest.fixture(autouse=True, scope="session")
def _init_logging():
    """Initialize logging once for the test session."""
    setup_logging()

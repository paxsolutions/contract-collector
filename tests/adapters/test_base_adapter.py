"""Tests for the base adapter and registry."""

import pytest

from collector.adapters.base import AdapterMeta, BaseAdapter
from collector.adapters.registry import ADAPTER_REGISTRY, get_adapter, register_adapter
from collector.core.schemas import RawRecord


class DummyAdapter(BaseAdapter):
    meta = AdapterMeta(name="dummy", base_url="https://example.com", description="Test adapter")

    async def extract(self, page):
        yield RawRecord(
            source_id="1",
            source_name="dummy",
            source_url="https://example.com/1",
            extracted={"title": "Test"},
        )


class TestRegistry:
    def test_register_and_get(self):
        register_adapter(DummyAdapter)
        assert "dummy" in ADAPTER_REGISTRY
        cls = get_adapter("dummy")
        assert cls is DummyAdapter

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown adapter"):
            get_adapter("nonexistent_adapter_xyz")


class TestBaseAdapter:
    def test_build_start_url(self):
        adapter = DummyAdapter()
        assert adapter.build_start_url() == "https://example.com"

    def test_checkpoint(self):
        adapter = DummyAdapter(checkpoint="last-123")
        assert adapter.checkpoint == "last-123"

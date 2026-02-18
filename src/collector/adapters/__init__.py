"""Source adapters — one module per procurement portal."""

from collector.adapters.base import BaseAdapter
from collector.adapters.registry import ADAPTER_REGISTRY, get_adapter

__all__ = ["BaseAdapter", "ADAPTER_REGISTRY", "get_adapter"]

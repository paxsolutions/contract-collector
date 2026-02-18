"""Adapter registry — auto-discover and look up adapters by name."""

from __future__ import annotations

from collector.adapters.base import BaseAdapter

# Populated by each adapter module at import time via ``register_adapter``.
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {}


def register_adapter(cls: type[BaseAdapter]) -> type[BaseAdapter]:
    """Class decorator that registers an adapter in the global registry."""
    ADAPTER_REGISTRY[cls.meta.name] = cls
    return cls


def get_adapter(name: str) -> type[BaseAdapter]:
    """Look up a registered adapter by name. Raises KeyError if not found."""
    if name not in ADAPTER_REGISTRY:
        available = ", ".join(sorted(ADAPTER_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown adapter '{name}'. Available: {available}")
    return ADAPTER_REGISTRY[name]

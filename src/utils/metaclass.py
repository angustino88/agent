"""Metaclass factory helper."""
from __future__ import annotations


def metaclass_factory(*bases: type) -> type:
    """Create a metaclass that inherits from the metaclasses of *bases*.

    Useful when a class needs to combine multiple metaclasses.
    """
    meta_types = tuple(dict.fromkeys(type(b) for b in bases))  # deduplicate

    class _CombinedMeta(*meta_types):
        pass

    return _CombinedMeta
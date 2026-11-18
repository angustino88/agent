"""List utility functions."""
from __future__ import annotations

import copy
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class ListUtil:
    """Advanced list manipulation utilities."""

    @staticmethod
    def strip_items(items: list[str], chars: str | None = None) -> list[str]:
        """Strip whitespace or specified characters from each string."""
        return [item.strip(chars) for item in items]

    @staticmethod
    def remove_duplicates(
        lists: list[Any] | tuple[list[Any], ...],
        merge: bool = True,
        sort: bool = True,
    ) -> list[Any] | tuple[list[Any], ...]:
        """Remove duplicate items from one or more lists.

        *merge*: when ``True`` merge all input lists before dedup.
        *sort*: when ``True`` the result is sorted.
        """
        def _dedup(lst: list[Any]) -> list[Any]:
            if sort:
                return sorted(set(lst))
            seen: list[Any] = []
            for item in lst:
                if item not in seen:
                    seen.append(item)
            return seen

        if merge:
            if isinstance(lists, tuple):
                merged: list[Any] = []
                for lst in lists:
                    merged.extend(lst)
                return _dedup(merged)
            return _dedup(lists)

        if isinstance(lists, tuple):
            return tuple(_dedup(lst) for lst in lists)
        return _dedup(lists)

    @staticmethod
    def find_duplicates(items: list[Any], with_index: bool = False) -> list[Any] | list[tuple[Any, int]]:
        """Find all duplicate items in a list.

        *with_index*: return ``(item, index)`` tuples instead of bare items.
        """
        seen: list[Any] = []
        dups: list[Any] = []
        for idx, item in enumerate(items):
            if item not in seen:
                seen.append(item)
            elif with_index:
                dups.append((item, idx))
            else:
                dups.append(item)
        return dups

    @staticmethod
    def all_unique(items: list[Any]) -> bool:
        """Return ``True`` if all elements are unique."""
        return len(items) == len(set(items))

    @staticmethod
    def all_same(items: list[Any]) -> bool:
        """Return ``True`` if all elements are equal."""
        return len(set(items)) <= 1

    @staticmethod
    def flatten(nested: list) -> list:
        """Recursively flatten a nested list."""
        result: list[Any] = []
        for item in nested:
            if isinstance(item, list):
                result.extend(ListUtil.flatten(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def chunk(items: list[Any], size: int) -> list[list[Any]]:
        """Split a list into chunks of *size*."""
        return [items[i:i + size] for i in range(0, len(items), size)]

    @staticmethod
    def transpose(matrix: list[list[Any]]) -> list[list[Any]]:
        """Transpose a 2-D list (matrix)."""
        if not matrix:
            return []
        return [list(row) for row in zip(*matrix)]

    @staticmethod
    def filter_items(items: list[Any], func: Callable[[Any], bool]) -> list[Any]:
        """Return items for which *func* returns ``True``."""
        return [item for item in items if func(item)]

    @staticmethod
    def find_first(items: list[Any], func: Callable[[Any], bool]) -> Any:
        """Return the first item matching *func*, or ``None``."""
        for item in items:
            if func(item):
                return item
        return None

    @staticmethod
    def find_last(items: list[Any], func: Callable[[Any], bool]) -> Any:
        """Return the last item matching *func*, or ``None``."""
        for item in reversed(items):
            if func(item):
                return item
        return None

    @staticmethod
    def index_of(items: list[Any], value: Any) -> int:
        """Return the index of the first occurrence of *value*, or ``-1``."""
        try:
            return items.index(value)
        except ValueError:
            return -1

    @staticmethod
    def group_by(items: list[Any], key: Callable[[Any], Any]) -> dict[Any, list[Any]]:
        """Group items by the result of *key(item)*.

        Example::

            group_by(["apple", "avocado", "banana"], key=lambda s: s[0])
            # → {"a": ["apple", "avocado"], "b": ["banana"]}
        """
        groups: dict[Any, list[Any]] = {}
        for item in items:
            k = key(item)
            groups.setdefault(k, []).append(item)
        return groups

    @staticmethod
    def partition(items: list[Any], predicate: Callable[[Any], bool]) -> tuple[list[Any], list[Any]]:
        """Split a list into two: ``(matches, non_matches)``."""
        yes: list[Any] = []
        no: list[Any] = []
        for item in items:
            (yes if predicate(item) else no).append(item)
        return yes, no

    @staticmethod
    def compact(items: list[Any]) -> list[Any]:
        """Remove ``None`` values from a list."""
        return [item for item in items if item is not None]

    @staticmethod
    def deep_copy(items: list[Any]) -> list[Any]:
        """Return a deep copy of the list."""
        return copy.deepcopy(items)

    @staticmethod
    def sliding_window(items: list[Any], size: int) -> list[list[Any]]:
        """Return overlapping windows of *size* across *items*.

        Example::

            sliding_window([1, 2, 3, 4], 2)  # → [[1,2], [2,3], [3,4]]
        """
        if size <= 0 or size > len(items):
            return []
        return [items[i:i + size] for i in range(len(items) - size + 1)]

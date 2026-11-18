from typing import TypeVar

T = TypeVar("T")

class Registry:
    """Typed key-based store shared by model, view, and controller layers."""
    def __init__(self) -> None:
        self._registry: dict[tuple[type, str | None], object] = {}

    def register(self, obj: object, key: str | None = None) -> None:
        """Register *obj* under its type and optional *key*. Raises if duplicate."""
        entry = (type(obj), key)
        if entry in self._registry:
            raise KeyError(
                f"'{type(obj).__name__}' key='{key}' is already registered."
            )
        self._registry[entry] = obj

    def register_or_update(self, obj: object, key: str | None = None) -> None:
        """Register *obj*, silently replacing any existing entry for the same type and *key*."""
        self._registry[(type(obj), key)] = obj

    def has(self, cls: type, key: str | None = None) -> bool:
        """Return ``True`` if an instance of *cls* for *key* is registered."""
        return (cls, key) in self._registry

    def get(self, cls: type[T], key: str | None = None) -> T:
        """Return the instance of *cls* for *key* (``LookupError`` if absent)."""
        try:
            return self._registry[(cls, key)]  # type: ignore[return-value]
        except KeyError:
            label = f"{cls.__name__}(key='{key}')" if key else cls.__name__
            raise LookupError(f"'{label}' is not registered.")

    def get_all(self, cls: type[T], *, subclasses: bool = False) -> list[T]:
        """Return all instances of *cls*.

        When *subclasses* is ``True``, also returns instances of subclasses of
        *cls* — useful for retrieving all models that implement an interface.
        """
        if subclasses:
            return [v for (c, _), v in self._registry.items() if issubclass(c, cls)]  # type: ignore[misc]
        return [v for (c, _), v in self._registry.items() if c is cls]  # type: ignore[misc]

    def unregister(self, cls: type, key: str | None = None) -> None:
        """Remove the entry for *cls* and *key*. Silent if not registered."""
        self._registry.pop((cls, key), None)

    def __len__(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        return f"<Registry entries={len(self._registry)}>"

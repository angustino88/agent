# Service Container (Dependency Injection)

> Thread-safe lazy-singleton dependency injection container. Register
> factories or pre-built instances; the container creates and caches
> singletons on first access.

---

## Imports

```python
from mvc import ServiceContainer
```

---

## Quick Start

```python
from mvc import ServiceContainer

container = ServiceContainer()

# Register a factory — instance created on first get()
container.register(DatabaseService, lambda: DatabaseService("localhost", 5432))

# Register a pre-built instance
container.register_instance(ConfigService, ConfigService.load("config.yml"))

# Retrieve (creates DatabaseService on first call, caches thereafter)
db = container.get(DatabaseService)
config = container.get(ConfigService)
```

---

## Factory Registration

The factory callable is invoked **once** — on the first `get()` call.
Subsequent calls return the cached singleton.

```python
class AppModel(BaseMainModel):
    def _configure(self) -> None:
        self._services = ServiceContainer()

        # Factory with dependencies
        self._services.register(HttpClient, lambda: HttpClient(
            base_url=self.get(ConfigModel).api_url,
            timeout=30,
        ))

        self._services.register(PackageService, lambda: PackageService(
            http=self._services.get(HttpClient),
        ))
```

---

## Instance Registration

For objects that are already constructed:

```python
container.register_instance(logging.Logger, logging.getLogger("app"))
container.register_instance(EventBus, bus)
```

---

## Retrieving Services

### `get(cls)` — raises if not registered

```python
http = container.get(HttpClient)
```

### `get_optional(cls)` — returns `None` if not registered

```python
cache = container.get_optional(CacheService)
if cache:
    cache.warm_up()
```

### `has(cls)` — check registration

```python
if container.has(DatabaseService):
    db = container.get(DatabaseService)
```

### `in` operator

```python
if DatabaseService in container:
    ...
```

---

## Reset & Clear

### Reset a single service (re-create on next `get()`)

```python
container.reset(HttpClient)
# Next get(HttpClient) will call the factory again
```

### Reset all cached instances

```python
container.reset()
# All factories will re-execute on next get()
```

### Clear everything (remove all registrations)

```python
container.clear()
```

---

## Thread Safety

All operations are thread-safe. Factory invocation uses a lock to prevent
double-creation under concurrent access:

```python
# Safe from multiple threads
def worker():
    db = container.get(DatabaseService)  # always the same instance
```

---

## Practical Example — Application Services

```python
class AppModel(BaseMainModel):
    def _setup(self) -> None:
        self._make(ConfigModel)
        self._make(ServiceGatewayModel)

    def _configure(self) -> None:
        svc = ServiceContainer()

        # Core services
        svc.register(HttpClient, lambda: HttpClient(
            base_url=self.get(ConfigModel).api_base_url,
        ))

        svc.register(AuthService, lambda: AuthService(
            http=svc.get(HttpClient),
            token_store=self.get(ConfigModel),
        ))

        svc.register(PackageService, lambda: PackageService(
            http=svc.get(HttpClient),
            auth=svc.get(AuthService),
        ))

        # Make available to sub-models
        self.register(svc, key="services")
```

Usage from a sub-model:

```python
class PackageModel(BaseModel):
    def init(self) -> None:
        svc = self.model.get(ServiceContainer, key="services")
        self._pkg_service = svc.get(PackageService)

    def search(self, query: str) -> list[dict]:
        return self._pkg_service.search(query)
```

---

## Practical Example — Testing with Mocks

```python
def test_package_model():
    container = ServiceContainer()

    # Register mock instead of real service
    mock_service = Mock(spec=PackageService)
    mock_service.search.return_value = [{"name": "curl"}]
    container.register_instance(PackageService, mock_service)

    model = PackageModel()
    model._pkg_service = container.get(PackageService)

    assert model.search("curl") == [{"name": "curl"}]
```

---

## API Reference

### `ServiceContainer()`

| Method | Returns | Description |
|---|---|---|
| `register(cls, factory)` | `None` | Register a lazy factory |
| `register_instance(cls, instance)` | `None` | Register a pre-built instance |
| `get(cls)` | `T` | Get singleton (creates if needed); raises `LookupError` |
| `get_optional(cls)` | `T \| None` | Get singleton or `None` |
| `has(cls)` | `bool` | Check if registered |
| `reset(cls=None)` | `None` | Drop cached instance(s); `None` = reset all |
| `clear()` | `None` | Remove all registrations |
| `__contains__(cls)` | `bool` | `cls in container` |

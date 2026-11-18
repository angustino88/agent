"""MVC framework — public API.

Provides base classes for Model–View–Controller architecture with an event
bus, command pipeline, task scheduling, lifecycle management, typed
registry, plugin system, service container, and typed events.
"""

from .base_controller import BaseController, BaseMainController
from .base_model import BaseModel, BaseMainModel
from .base_view import BaseView, BaseMainView, ViewState
from .base_thread import BaseThread, EHandle
from .command import Command, MacroCommand
from .console import WidgetConsole, MessageBoxConsole
from .dependency import UIDependency
from .event import Event
from .event_bus import EventBus, throttle, debounce
from .event_logger import log_events
from .icon import IconMixin
from .lifecycle import Lifecycle, State
from .middleware import Middleware, LoggingMiddleware, MiddlewarePipeline
from .plugin import Plugin, PluginContext, PluginManager
from .registry import Registry
from .router import Router, Route
from .service import ServiceContainer
from .signal import Signal
from .slot_guard import slot_guard
from .state_machine import StateMachine
from .task_engine import TaskEngine
from .task_runner import TaskRunner
from .task_schedule import Schedule, ScheduledTask, task
from .worker_thread import WorkerThread, WorkerRelay
from .config import (
    MarkedConfig,
    RuntimeDir,
    BundledPath,
    LogFile,
    ConfigFile,
    SecretField,
    ServiceUrl,
    EnvOverride,
    _FieldMarker,
    _RuntimeDirMarker,
    _BundledPathMarker,
    _LogFileMarker,
    _ConfigFileMarker,
    _SecretFieldMarker,
    _ServiceUrlMarker,
    _EnvOverrideMarker,
)

__all__ = [
    # MVC base classes
    "BaseController", "BaseMainController",
    "BaseModel", "BaseMainModel",
    "BaseView", "BaseMainView", "ViewState",
    # ViewModel no longer part of MVC public API in this branch
    # Threading
    "BaseThread", "EHandle",
    # Command pattern
    "Command", "MacroCommand",
    # Console / logging
    "WidgetConsole", "MessageBoxConsole",
    "log_events",
    # Event system
    "Event",
    "EventBus", "throttle", "debounce",
    "Signal",
    # UI helpers
    "UIDependency", "IconMixin", "slot_guard",
    # Lifecycle & state
    "Lifecycle", "State",
    "StateMachine",
    # Middleware
    "Middleware", "LoggingMiddleware", "MiddlewarePipeline",
    # Plugin system
    "Plugin", "PluginContext", "PluginManager",
    # Registry
    "Registry",
    # Routing
    "Router", "Route",
    # Service container
    "ServiceContainer",
    # Task scheduling
    "TaskEngine", "TaskRunner",
    "Schedule", "ScheduledTask", "task",
]

from functools import wraps
import logging


def log_events(*event_names, logger=None, logger_name=None):
    """
    Class decorator factory to log specified Qt event methods safely.
    Supports direct logger or nested logger attribute via logger_name.
    """
    def get_nested_attr(obj, attr_path, default=None):
        try:
            for attr in attr_path.split('.'):
                obj = getattr(obj, attr)
            return obj
        except AttributeError:
            return default

    def decorator(cls):
        for event_name in event_names:
            orig_event = getattr(cls, event_name, None)

            def make_wrapper(orig, name):
                def event_wrapper(self, event):
                    msg = f"{self.objectName() or cls.__name__}: {name}"
                    log_obj = None
                    if logger_name:
                        log_obj = get_nested_attr(self, logger_name, None)
                    if log_obj is None:
                        log_obj = logger or logging.getLogger(__name__)
                    try:
                        log_obj.debug(msg)
                    except Exception:
                        pass

                    if orig:
                        return orig(self, event)
                    parent = getattr(super(cls, self), name, None)
                    if parent:
                        return parent(event)

                if orig is not None:
                    event_wrapper = wraps(orig)(event_wrapper)
                return event_wrapper

            setattr(cls, event_name, make_wrapper(orig_event, event_name))
        return cls

    return decorator
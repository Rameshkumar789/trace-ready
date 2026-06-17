"""ASGI API surface for TraceReady backend services."""

__all__ = ["app", "create_app"]


def __getattr__(name: str):
    if name in __all__:
        from traceready_backend.api.main import app, create_app

        return {"app": app, "create_app": create_app}[name]
    raise AttributeError(name)

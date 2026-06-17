"""Vercel-compatible ASGI entrypoint.

Vercel can load this module while the implementation remains in the
installable `traceready_backend` package.
"""

from traceready_backend.api.main import app

__all__ = ["app"]

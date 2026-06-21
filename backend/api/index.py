"""Vercel-compatible ASGI entrypoint.

Vercel can load this module while the implementation remains in the
installable `bellwether_backend` package.
"""

from bellwether_backend.api.main import app

__all__ = ["app"]

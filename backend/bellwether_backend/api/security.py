from __future__ import annotations

from secrets import compare_digest

from fastapi import Header, HTTPException, Request

from bellwether_backend.api.config import ServiceSettings


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def require_internal_token(
    request: Request,
    authorization: str | None = Header(default=None),
    x_bellwether_internal_token: str | None = Header(default=None),
) -> None:
    settings: ServiceSettings = request.app.state.settings
    configured_token = settings.internal_api_token
    if not configured_token:
        raise HTTPException(status_code=503, detail="Internal API token is not configured.")

    supplied_token = x_bellwether_internal_token or _extract_bearer_token(authorization)
    if not supplied_token or not compare_digest(supplied_token, configured_token):
        raise HTTPException(status_code=401, detail="Invalid internal API token.")

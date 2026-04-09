"""OAuth / OpenID Connect client for SSO integration."""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from app.config import settings


class OAuthClient:
    """Thin async wrapper around an OpenID Connect provider.

    Discovery, authorization, token exchange, and user-info are all driven
    by ``settings.oauth_discovery_url``.  The class lazily fetches the OIDC
    discovery document on the first call that needs endpoint URLs.
    """

    def __init__(self) -> None:
        self._discovery_doc: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def _discover(self) -> dict[str, Any]:
        """Fetch and cache the OIDC discovery document."""
        if self._discovery_doc is not None:
            return self._discovery_doc

        url = settings.oauth_discovery_url
        if not url:
            raise RuntimeError(
                "OAuth discovery URL is not configured "
                "(settings.oauth_discovery_url is empty)"
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            self._discovery_doc = resp.json()

        return self._discovery_doc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_authorization_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        scopes: list[str] | None = None,
    ) -> str:
        """Build and return the authorization URL for the SSO provider.

        Parameters
        ----------
        redirect_uri:
            The callback URL registered with the provider.
        state:
            Optional opaque value for CSRF protection.
        scopes:
            OAuth scopes to request.  Defaults to ``["openid", "email", "profile"]``.
        """
        doc = await self._discover()
        auth_endpoint: str = doc["authorization_endpoint"]

        params: dict[str, str] = {
            "client_id": settings.oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or ["openid", "email", "profile"]),
        }
        if state:
            params["state"] = state

        return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange an authorisation *code* for tokens.

        Returns the full token response dict (``access_token``,
        ``id_token``, ``refresh_token``, ``expires_in``, etc.).
        """
        doc = await self._discover()
        token_endpoint: str = doc["token_endpoint"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": settings.oauth_client_id,
                    "client_secret": settings.oauth_client_secret,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch the authenticated user's profile from the provider's
        user-info endpoint.

        Returns the raw JSON dict (typically contains ``sub``, ``email``,
        ``name``, ``picture``, etc.).
        """
        doc = await self._discover()
        userinfo_endpoint: str = doc["userinfo_endpoint"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                userinfo_endpoint,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()


# Module-level singleton for convenience.
oauth_client = OAuthClient()

"""
OAuth2 Authentication Handler for TickTick V1 API.

This module implements the OAuth2 authorization code flow for TickTick's
official Open API.

OAuth2 Flow:
    1. Generate authorization URL
    2. User authorizes and is redirected with authorization code
    3. Exchange authorization code for access token
    4. Use access token for API requests
"""

from __future__ import annotations

import base64
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from ticktick_mcp.constants import (
    DEFAULT_TIMEOUT,
    OAUTH_SCOPES,
    TICKTICK_OAUTH_BASE,
)
from ticktick_mcp.exceptions import TickTickOAuthError

logger = logging.getLogger(__name__)


@dataclass
class OAuth2Token:
    """OAuth2 token data."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_in is None:
            return False  # Assume non-expiring if not specified
        expiry_time = self.created_at + timedelta(seconds=self.expires_in)
        # Add 60 second buffer
        return datetime.now(timezone.utc) >= (expiry_time - timedelta(seconds=60))

    @property
    def authorization_header(self) -> str:
        """Get the Authorization header value."""
        return f"{self.token_type} {self.access_token}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OAuth2Token:
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            created_at=created_at,
        )


class OAuth2Handler:
    """
    Handles OAuth2 authentication for TickTick V1 API.

    Usage:
        handler = OAuth2Handler(client_id, client_secret, redirect_uri)

        # Step 1: Get authorization URL
        auth_url, state = handler.get_authorization_url()

        # Step 2: User authorizes and you receive the code
        # ... redirect user to auth_url ...
        # ... receive code from callback ...

        # Step 3: Exchange code for token
        token = await handler.exchange_code(code, state)

        # Step 4: Use token
        access_token = token.access_token
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or OAUTH_SCOPES.copy()
        self.timeout = timeout

        self._token: OAuth2Token | None = None
        self._state: str | None = None

    @property
    def token(self) -> OAuth2Token | None:
        """Get the current token."""
        return self._token

    @token.setter
    def token(self, value: OAuth2Token | None) -> None:
        """Set the current token."""
        self._token = value

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid (non-expired) token."""
        return self._token is not None and not self._token.is_expired

    @property
    def access_token(self) -> str | None:
        """Get the access token if available and valid."""
        if self.is_authenticated and self._token:
            return self._token.access_token
        return None

    def set_access_token(self, access_token: str) -> None:
        """Set an access token directly (for pre-obtained tokens)."""
        self._token = OAuth2Token(access_token=access_token)

    # =========================================================================
    # Authorization URL Generation
    # =========================================================================

    def get_authorization_url(self, state: str | None = None) -> tuple[str, str]:
        """
        Generate the authorization URL for the OAuth2 flow.

        Args:
            state: Optional state parameter. If not provided, a random one is generated.

        Returns:
            Tuple of (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        self._state = state

        params = {
            "client_id": self.client_id,
            "scope": " ".join(self.scopes),
            "state": state,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }

        auth_url = f"{TICKTICK_OAUTH_BASE}/authorize?{urlencode(params)}"
        logger.debug("Generated authorization URL: %s", auth_url)

        return auth_url, state

    # =========================================================================
    # Token Exchange
    # =========================================================================

    def _get_basic_auth_header(self) -> str:
        """Get the Basic Auth header for token requests."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> OAuth2Token:
        """
        Exchange an authorization code for an access token.

        Args:
            code: The authorization code from the callback
            state: The state parameter to verify (optional but recommended)

        Returns:
            OAuth2Token with the access token

        Raises:
            TickTickOAuthError: If token exchange fails
        """
        # Verify state if provided
        if state is not None and self._state is not None and state != self._state:
            raise TickTickOAuthError(
                "State mismatch - possible CSRF attack",
                oauth_error="invalid_state",
            )

        token_url = f"{TICKTICK_OAUTH_BASE}/token"

        # Prepare request data
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "scope": " ".join(self.scopes),
            "redirect_uri": self.redirect_uri,
        }

        headers = {
            "Authorization": self._get_basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        logger.debug("Exchanging authorization code for token")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    token_url,
                    data=data,
                    headers=headers,
                )
            except httpx.RequestError as e:
                raise TickTickOAuthError(
                    f"Token exchange request failed: {e}",
                ) from e

            if not response.is_success:
                self._handle_token_error(response)

            token_data = response.json()

        self._token = OAuth2Token(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
        )

        logger.info("Successfully obtained access token")
        return self._token

    async def refresh_access_token(self) -> OAuth2Token:
        """
        Refresh the access token using the refresh token.

        Returns:
            OAuth2Token with the new access token

        Raises:
            TickTickOAuthError: If refresh fails or no refresh token available
        """
        if self._token is None or self._token.refresh_token is None:
            raise TickTickOAuthError(
                "No refresh token available",
                oauth_error="invalid_grant",
            )

        token_url = f"{TICKTICK_OAUTH_BASE}/token"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._token.refresh_token,
            "scope": " ".join(self.scopes),
        }

        headers = {
            "Authorization": self._get_basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        logger.debug("Refreshing access token")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    token_url,
                    data=data,
                    headers=headers,
                )
            except httpx.RequestError as e:
                raise TickTickOAuthError(
                    f"Token refresh request failed: {e}",
                ) from e

            if not response.is_success:
                self._handle_token_error(response)

            token_data = response.json()

        self._token = OAuth2Token(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token", self._token.refresh_token),
            scope=token_data.get("scope"),
        )

        logger.info("Successfully refreshed access token")
        return self._token

    def _handle_token_error(self, response: httpx.Response) -> None:
        """Handle error response from token endpoint."""
        try:
            error_data = response.json()
            oauth_error = error_data.get("error")
            error_description = error_data.get("error_description")
        except Exception:
            oauth_error = None
            error_description = response.text

        raise TickTickOAuthError(
            f"Token request failed: {error_description or response.text}",
            oauth_error=oauth_error,
            oauth_error_description=error_description,
            details={"status_code": response.status_code},
        )

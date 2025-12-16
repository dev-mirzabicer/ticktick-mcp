"""
Session-Based Authentication Handler for TickTick V2 API.

This module implements username/password authentication for TickTick's
unofficial V2 API.

Authentication Flow:
    1. POST /api/v2/user/signon with credentials
    2. Receive token and session cookies
    3. Use token in Authorization header and cookies in subsequent requests
"""

from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from ticktick_mcp.constants import (
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    TICKTICK_API_BASE_V2,
    X_DEVICE_TEMPLATE,
)
from ticktick_mcp.exceptions import TickTickSessionError

logger = logging.getLogger(__name__)


@dataclass
class SessionToken:
    """V2 API session token data."""

    token: str
    user_id: str
    username: str
    inbox_id: str
    user_code: str | None = None
    is_pro: bool = False
    pro_start_date: str | None = None
    pro_end_date: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Cookies captured from the response
    cookies: dict[str, str] = field(default_factory=dict)

    @property
    def authorization_header(self) -> str:
        """Get the Authorization header value."""
        return f"Bearer {self.token}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "token": self.token,
            "user_id": self.user_id,
            "username": self.username,
            "inbox_id": self.inbox_id,
            "user_code": self.user_code,
            "is_pro": self.is_pro,
            "pro_start_date": self.pro_start_date,
            "pro_end_date": self.pro_end_date,
            "created_at": self.created_at.isoformat(),
            "cookies": self.cookies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionToken:
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return cls(
            token=data["token"],
            user_id=data["user_id"],
            username=data["username"],
            inbox_id=data["inbox_id"],
            user_code=data.get("user_code"),
            is_pro=data.get("is_pro", False),
            pro_start_date=data.get("pro_start_date"),
            pro_end_date=data.get("pro_end_date"),
            created_at=created_at,
            cookies=data.get("cookies", {}),
        )


class SessionHandler:
    """
    Handles session-based authentication for TickTick V2 API.

    Usage:
        handler = SessionHandler(device_id="unique_id")

        # Authenticate
        session = await handler.authenticate("user@example.com", "password")

        # Use session
        access_token = session.token
        cookies = session.cookies
    """

    def __init__(
        self,
        device_id: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.device_id = device_id or secrets.token_hex(12)
        self.timeout = timeout
        self.user_agent = user_agent

        self._session: SessionToken | None = None

    @property
    def session(self) -> SessionToken | None:
        """Get the current session."""
        return self._session

    @session.setter
    def session(self, value: SessionToken | None) -> None:
        """Set the current session."""
        self._session = value

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid session."""
        return self._session is not None

    @property
    def token(self) -> str | None:
        """Get the session token if available."""
        if self._session:
            return self._session.token
        return None

    @property
    def inbox_id(self) -> str | None:
        """Get the inbox ID if available."""
        if self._session:
            return self._session.inbox_id
        return None

    def _get_x_device_header(self) -> str:
        """Get the x-device header JSON string."""
        header = X_DEVICE_TEMPLATE.copy()
        header["id"] = self.device_id
        return json.dumps(header)

    def _get_headers(self) -> dict[str, str]:
        """Get headers for authentication requests."""
        return {
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            "x-device": self._get_x_device_header(),
        }

    async def authenticate(
        self,
        username: str,
        password: str,
    ) -> SessionToken:
        """
        Authenticate with username and password.

        Args:
            username: TickTick account username/email
            password: TickTick account password

        Returns:
            SessionToken with authentication credentials

        Raises:
            TickTickSessionError: If authentication fails
        """
        url = f"{TICKTICK_API_BASE_V2}/user/signon"
        params = {"wc": "true", "remember": "true"}
        payload = {"username": username, "password": password}
        headers = self._get_headers()

        logger.debug("Authenticating user: %s", username)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    params=params,
                    json=payload,
                    headers=headers,
                )
            except httpx.RequestError as e:
                raise TickTickSessionError(
                    f"Authentication request failed: {e}",
                ) from e

            if not response.is_success:
                self._handle_auth_error(response)

            data = response.json()

        # Check for 2FA requirement
        if "authId" in data and "token" not in data:
            raise TickTickSessionError(
                "Two-factor authentication required",
                requires_2fa=True,
                auth_id=data.get("authId"),
                details={"expire_time": data.get("expireTime")},
            )

        # Extract cookies
        cookies: dict[str, str] = {}
        for cookie in response.cookies.jar:
            cookies[cookie.name] = cookie.value

        # Also add the token as a cookie (required by V2 API)
        if "t" not in cookies and "token" in data:
            cookies["t"] = data["token"]

        self._session = SessionToken(
            token=data["token"],
            user_id=str(data.get("userId", "")),
            username=data.get("username", username),
            inbox_id=data.get("inboxId", ""),
            user_code=data.get("userCode"),
            is_pro=data.get("pro", False),
            pro_start_date=data.get("proStartDate"),
            pro_end_date=data.get("proEndDate"),
            cookies=cookies,
        )

        logger.info("Successfully authenticated user: %s", username)
        return self._session

    async def authenticate_2fa(
        self,
        auth_id: str,
        totp_code: str,
    ) -> SessionToken:
        """
        Complete 2FA authentication.

        Args:
            auth_id: The authId from the initial sign-on response
            totp_code: The TOTP code from the authenticator app

        Returns:
            SessionToken with authentication credentials

        Raises:
            TickTickSessionError: If 2FA verification fails
        """
        url = f"{TICKTICK_API_BASE_V2}/user/signon/totp"
        payload = {
            "authId": auth_id,
            "code": totp_code,
        }
        headers = self._get_headers()

        logger.debug("Completing 2FA authentication")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
            except httpx.RequestError as e:
                raise TickTickSessionError(
                    f"2FA verification request failed: {e}",
                ) from e

            if not response.is_success:
                self._handle_auth_error(response)

            data = response.json()

        # Extract cookies
        cookies: dict[str, str] = {}
        for cookie in response.cookies.jar:
            cookies[cookie.name] = cookie.value

        if "t" not in cookies and "token" in data:
            cookies["t"] = data["token"]

        self._session = SessionToken(
            token=data["token"],
            user_id=str(data.get("userId", "")),
            username=data.get("username", ""),
            inbox_id=data.get("inboxId", ""),
            user_code=data.get("userCode"),
            is_pro=data.get("pro", False),
            pro_start_date=data.get("proStartDate"),
            pro_end_date=data.get("proEndDate"),
            cookies=cookies,
        )

        logger.info("Successfully completed 2FA authentication")
        return self._session

    def set_session(self, session: SessionToken) -> None:
        """Set an existing session directly."""
        self._session = session

    def clear_session(self) -> None:
        """Clear the current session."""
        self._session = None

    def _handle_auth_error(self, response: httpx.Response) -> None:
        """Handle error response from auth endpoints."""
        try:
            error_data = response.json()
            error_message = error_data.get("message", response.text)
        except Exception:
            error_data = None
            error_message = response.text

        raise TickTickSessionError(
            f"Authentication failed: {error_message}",
            details={
                "status_code": response.status_code,
                "response": error_data or response.text,
            },
        )

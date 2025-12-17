"""
Base HTTP Client for TickTick API.

This module provides a base async HTTP client with common functionality
shared between V1 and V2 API clients.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, TypeVar

import httpx

from ticktick_mcp.constants import APIVersion, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT
from ticktick_mcp.exceptions import (
    TickTickAPIError,
    TickTickAuthenticationError,
    TickTickForbiddenError,
    TickTickNotFoundError,
    TickTickQuotaExceededError,
    TickTickRateLimitError,
    TickTickServerError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseTickTickClient")


class BaseTickTickClient(ABC):
    """
    Abstract base class for TickTick API clients.

    Provides common HTTP functionality, error handling, and lifecycle management.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._is_authenticated = False

    # =========================================================================
    # Abstract Properties
    # =========================================================================

    @property
    @abstractmethod
    def api_version(self) -> APIVersion:
        """Return the API version this client implements."""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for API requests."""
        ...

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        ...

    # =========================================================================
    # HTTP Client Management
    # =========================================================================

    def _get_base_headers(self) -> dict[str, str]:
        """Get base headers for all requests."""
        return {
            "User-Agent": self._user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @abstractmethod
    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers. Must be implemented by subclasses."""
        ...

    def _get_headers(self) -> dict[str, str]:
        """Get all headers for requests."""
        headers = self._get_base_headers()
        if self.is_authenticated:
            headers.update(self._get_auth_headers())
        return headers

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure the HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self._timeout),
                headers=self._get_base_headers(),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    async def __aenter__(self: T) -> T:
        """Enter async context manager."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    # =========================================================================
    # Error Handling
    # =========================================================================

    # TickTick API error codes that map to specific exceptions
    # Note: TickTick often returns HTTP 500 with semantic error codes in the body
    _NOT_FOUND_ERROR_CODES = frozenset({
        "task_not_found",
        "project_not_found",
        "tag_not_found",
        "tag_not_exist",  # V2 API uses this for tag operations
        "folder_not_found",
        "group_not_found",
        "resource_not_found",
        "not_found",
    })

    _FORBIDDEN_ERROR_CODES = frozenset({
        "access_forbidden",
        "forbidden",
        "permission_denied",
    })

    _AUTH_ERROR_CODES = frozenset({
        "unauthorized",
        "invalid_token",
        "token_expired",
        "username_password_not_match",
        "incorrect_password_too_many_times",
    })

    def _handle_error_response(
        self,
        response: httpx.Response,
        endpoint: str,
    ) -> None:
        """Handle error responses and raise appropriate exceptions.

        TickTick's API often returns HTTP 500 for semantic errors like "not found".
        We check both the HTTP status code AND the errorCode in the response body
        to determine the actual error type.
        """
        status_code = response.status_code

        # Try to parse error body
        try:
            error_body = response.json()
            error_message = error_body.get("errorMessage") or error_body.get("message", response.text)
            error_code = error_body.get("errorCode", "").lower()
        except (json.JSONDecodeError, ValueError):
            error_body = None
            error_message = response.text
            error_code = ""

        # First, check error codes in response body (takes precedence over HTTP status)
        # TickTick often returns HTTP 500 with semantic error codes
        if error_code:
            if error_code in self._NOT_FOUND_ERROR_CODES:
                raise TickTickNotFoundError(
                    f"Resource not found: {error_message}",
                    endpoint=endpoint,
                    api_version=self.api_version.value,
                )
            elif error_code in self._FORBIDDEN_ERROR_CODES:
                raise TickTickForbiddenError(
                    f"Access forbidden: {error_message}",
                    endpoint=endpoint,
                    response_body=response.text,
                    api_version=self.api_version.value,
                )
            elif error_code in self._AUTH_ERROR_CODES:
                raise TickTickAuthenticationError(
                    f"Authentication failed: {error_message}",
                    details={"endpoint": endpoint, "response": error_body, "error_code": error_code},
                )

        # Fall back to HTTP status code based handling
        if status_code == 401:
            raise TickTickAuthenticationError(
                f"Authentication failed: {error_message}",
                details={"endpoint": endpoint, "response": error_body},
            )
        elif status_code == 403:
            raise TickTickForbiddenError(
                f"Access forbidden: {error_message}",
                endpoint=endpoint,
                response_body=response.text,
                api_version=self.api_version.value,
            )
        elif status_code == 404:
            raise TickTickNotFoundError(
                f"Resource not found: {error_message}",
                endpoint=endpoint,
                api_version=self.api_version.value,
            )
        elif status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise TickTickRateLimitError(
                "Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None,
                endpoint=endpoint,
                api_version=self.api_version.value,
            )
        elif status_code >= 500:
            # Check for quota exceeded in response body
            if error_body and error_body.get("id2error"):
                for error in error_body["id2error"].values():
                    if error == "EXCEED_QUOTA":
                        raise TickTickQuotaExceededError(
                            "Account quota exceeded",
                            endpoint=endpoint,
                            api_version=self.api_version.value,
                        )

            raise TickTickServerError(
                f"Server error: {error_message}",
                status_code=status_code,
                response_body=response.text,
                endpoint=endpoint,
                api_version=self.api_version.value,
            )
        else:
            # Check for quota exceeded in response body
            if error_body and error_body.get("id2error"):
                for error in error_body["id2error"].values():
                    if error == "EXCEED_QUOTA":
                        raise TickTickQuotaExceededError(
                            "Account quota exceeded",
                            endpoint=endpoint,
                            api_version=self.api_version.value,
                        )

            raise TickTickAPIError(
                f"API error: {error_message}",
                status_code=status_code,
                response_body=response.text,
                endpoint=endpoint,
                api_version=self.api_version.value,
            )

    # =========================================================================
    # HTTP Methods
    # =========================================================================

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> httpx.Response:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            require_auth: Whether authentication is required

        Returns:
            httpx.Response object

        Raises:
            TickTickAuthenticationError: If auth required but not authenticated
            TickTickAPIError: On API errors
        """
        if require_auth and not self.is_authenticated:
            raise TickTickAuthenticationError(
                f"Authentication required for {self.api_version.value} API",
                details={"endpoint": endpoint},
            )

        client = await self._ensure_client()

        # Merge headers
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        logger.debug(
            "Making %s request to %s%s",
            method,
            self.base_url,
            endpoint,
        )

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=request_headers,
            )
        except httpx.TimeoutException as e:
            raise TickTickAPIError(
                f"Request timeout: {endpoint}",
                endpoint=endpoint,
                api_version=self.api_version.value,
                details={"timeout": self._timeout},
            ) from e
        except httpx.RequestError as e:
            raise TickTickAPIError(
                f"Request failed: {e}",
                endpoint=endpoint,
                api_version=self.api_version.value,
            ) from e

        # Handle errors
        if not response.is_success:
            self._handle_error_response(response, endpoint)

        return response

    async def _get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> httpx.Response:
        """Make a GET request."""
        return await self._request(
            "GET",
            endpoint,
            params=params,
            headers=headers,
            require_auth=require_auth,
        )

    async def _post(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> httpx.Response:
        """Make a POST request."""
        return await self._request(
            "POST",
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            require_auth=require_auth,
        )

    async def _put(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> httpx.Response:
        """Make a PUT request."""
        return await self._request(
            "PUT",
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            require_auth=require_auth,
        )

    async def _delete(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> httpx.Response:
        """Make a DELETE request."""
        return await self._request(
            "DELETE",
            endpoint,
            params=params,
            headers=headers,
            require_auth=require_auth,
        )

    async def _get_json(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> Any:
        """Make a GET request and return JSON response.

        Note: V1 API returns HTTP 200 with empty body for nonexistent resources.
        We handle this by raising TickTickNotFoundError.
        """
        response = await self._get(
            endpoint,
            params=params,
            headers=headers,
            require_auth=require_auth,
        )
        # Handle empty response body (V1 returns HTTP 200 with empty body for nonexistent resources)
        if not response.content or response.content.strip() == b"":
            raise TickTickNotFoundError(
                f"Resource not found (empty response)",
                endpoint=endpoint,
                api_version=self.api_version.value,
            )
        return response.json()

    async def _post_json(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        require_auth: bool = True,
    ) -> Any:
        """Make a POST request and return JSON response."""
        response = await self._post(
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            require_auth=require_auth,
        )
        return response.json()

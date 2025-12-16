"""
TickTick MCP Settings and Configuration.

This module provides configuration management using pydantic-settings,
supporting both environment variables and explicit configuration.

Both V1 (OAuth2) and V2 (Session) credentials are REQUIRED for full functionality.
"""

from __future__ import annotations

import secrets
from functools import cached_property
from typing import Any

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ticktick_mcp.constants import DEFAULT_TIMEOUT, OAUTH_SCOPES, X_DEVICE_TEMPLATE
from ticktick_mcp.exceptions import TickTickConfigurationError


class TickTickSettings(BaseSettings):
    """
    TickTick MCP configuration settings.

    All credentials are required for full API functionality.
    The server requires both V1 (OAuth2) and V2 (Session) authentication.

    Environment Variables:
        V1 (OAuth2):
            TICKTICK_CLIENT_ID: OAuth2 client ID
            TICKTICK_CLIENT_SECRET: OAuth2 client secret
            TICKTICK_REDIRECT_URI: OAuth2 redirect URI
            TICKTICK_ACCESS_TOKEN: Pre-obtained OAuth2 access token (optional)
            TICKTICK_REFRESH_TOKEN: OAuth2 refresh token (optional)

        V2 (Session):
            TICKTICK_USERNAME: Account username/email
            TICKTICK_PASSWORD: Account password

        General:
            TICKTICK_TIMEOUT: Request timeout in seconds (default: 30)
            TICKTICK_TIMEZONE: Default timezone (default: UTC)
    """

    model_config = SettingsConfigDict(
        env_prefix="TICKTICK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # V1 OAuth2 Credentials
    # =========================================================================

    client_id: str = Field(
        default="",
        description="OAuth2 client ID from TickTick Developer Center",
    )
    client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="OAuth2 client secret",
    )
    redirect_uri: str = Field(
        default="http://localhost:8080/callback",
        description="OAuth2 redirect URI",
    )
    access_token: SecretStr | None = Field(
        default=None,
        description="Pre-obtained OAuth2 access token",
    )
    refresh_token: SecretStr | None = Field(
        default=None,
        description="OAuth2 refresh token for token renewal",
    )

    # =========================================================================
    # V2 Session Credentials
    # =========================================================================

    username: str = Field(
        default="",
        description="TickTick account username/email",
    )
    password: SecretStr = Field(
        default=SecretStr(""),
        description="TickTick account password",
    )

    # =========================================================================
    # General Settings
    # =========================================================================

    timeout: float = Field(
        default=DEFAULT_TIMEOUT,
        description="Request timeout in seconds",
        ge=1.0,
        le=300.0,
    )
    timezone: str = Field(
        default="UTC",
        description="Default timezone for date operations",
    )
    device_id: str = Field(
        default_factory=lambda: secrets.token_hex(12),
        description="Unique device identifier for V2 API",
    )

    # =========================================================================
    # Validation
    # =========================================================================

    @model_validator(mode="after")
    def validate_credentials(self) -> "TickTickSettings":
        """Validate that required credentials are present."""
        # We don't raise errors here - we'll check at runtime
        # This allows the settings to be instantiated even if incomplete
        return self

    # =========================================================================
    # Credential Checks
    # =========================================================================

    @property
    def has_v1_credentials(self) -> bool:
        """Check if V1 OAuth2 credentials are configured."""
        return bool(
            self.client_id
            and self.client_secret.get_secret_value()
        )

    @property
    def has_v1_token(self) -> bool:
        """Check if a V1 access token is available."""
        return bool(self.access_token and self.access_token.get_secret_value())

    @property
    def has_v2_credentials(self) -> bool:
        """Check if V2 session credentials are configured."""
        return bool(
            self.username
            and self.password.get_secret_value()
        )

    @property
    def is_fully_configured(self) -> bool:
        """Check if all required credentials are configured."""
        return self.has_v1_credentials and self.has_v2_credentials

    def validate_v1_ready(self) -> None:
        """Validate V1 API is ready for use. Raises if not configured."""
        if not self.has_v1_credentials:
            missing = []
            if not self.client_id:
                missing.append("TICKTICK_CLIENT_ID")
            if not self.client_secret.get_secret_value():
                missing.append("TICKTICK_CLIENT_SECRET")
            raise TickTickConfigurationError(
                "V1 OAuth2 credentials not configured",
                missing_config=missing,
            )

    def validate_v2_ready(self) -> None:
        """Validate V2 API is ready for use. Raises if not configured."""
        if not self.has_v2_credentials:
            missing = []
            if not self.username:
                missing.append("TICKTICK_USERNAME")
            if not self.password.get_secret_value():
                missing.append("TICKTICK_PASSWORD")
            raise TickTickConfigurationError(
                "V2 session credentials not configured",
                missing_config=missing,
            )

    def validate_all_ready(self) -> None:
        """Validate both V1 and V2 APIs are ready. Raises if not configured."""
        errors: list[str] = []
        missing: list[str] = []

        if not self.has_v1_credentials:
            errors.append("V1 OAuth2 credentials incomplete")
            if not self.client_id:
                missing.append("TICKTICK_CLIENT_ID")
            if not self.client_secret.get_secret_value():
                missing.append("TICKTICK_CLIENT_SECRET")

        if not self.has_v2_credentials:
            errors.append("V2 session credentials incomplete")
            if not self.username:
                missing.append("TICKTICK_USERNAME")
            if not self.password.get_secret_value():
                missing.append("TICKTICK_PASSWORD")

        if errors:
            raise TickTickConfigurationError(
                f"Configuration incomplete: {'; '.join(errors)}",
                missing_config=missing,
            )

    # =========================================================================
    # Helper Properties
    # =========================================================================

    @cached_property
    def oauth_scopes(self) -> list[str]:
        """Get OAuth2 scopes."""
        return OAUTH_SCOPES.copy()

    @cached_property
    def x_device_header(self) -> dict[str, Any]:
        """Get the x-device header for V2 API."""
        header = X_DEVICE_TEMPLATE.copy()
        header["id"] = self.device_id
        return header

    def get_v1_access_token(self) -> str | None:
        """Get the V1 access token value if available."""
        if self.access_token:
            return self.access_token.get_secret_value()
        return None

    def get_v2_password(self) -> str:
        """Get the V2 password value."""
        return self.password.get_secret_value()


# Global settings instance (lazy initialization)
_settings: TickTickSettings | None = None


def get_settings() -> TickTickSettings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = TickTickSettings()
    return _settings


def configure_settings(**kwargs: Any) -> TickTickSettings:
    """Configure settings with explicit values."""
    global _settings
    _settings = TickTickSettings(**kwargs)
    return _settings

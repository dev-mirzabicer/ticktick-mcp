"""
Tests for environment variable support in constants module.
"""

import os
from unittest.mock import patch


def test_constants_default_domain():
    """Test that constants use default domain when no env var is set."""
    with patch.dict(os.environ, {}, clear=True):
        from importlib import reload
        import ticktick_sdk.constants as constants

        reload(constants)

        assert "ticktick.com" in constants.TICKTICK_API_BASE_V1
        assert "ticktick.com" in constants.TICKTICK_API_BASE_V2
        assert "ticktick.com" in constants.TICKTICK_OAUTH_BASE


def test_constants_use_custom_domain():
    """Test that constants are updated when domain is changed."""
    with patch.dict(os.environ, {"TICKTICK_DOMAIN": "dida365.com"}):
        from importlib import reload
        import ticktick_sdk.constants as constants

        reload(constants)

        assert "dida365.com" in constants.TICKTICK_API_BASE_V1
        assert "dida365.com" in constants.TICKTICK_API_BASE_V2
        assert "dida365.com" in constants.TICKTICK_OAUTH_BASE

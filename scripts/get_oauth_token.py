#!/usr/bin/env python3
"""
TickTick OAuth2 Token Acquisition Script.

This script guides you through the OAuth2 flow to obtain an access token
for the TickTick V1 API.

Usage:
    python scripts/get_oauth_token.py           # Auto mode (opens browser)
    python scripts/get_oauth_token.py --manual  # Manual mode (SSH-friendly)

The script will:
1. Generate an authorization URL
2. Either open browser (auto) or print URL for manual visit (manual)
3. Exchange the authorization code for an access token
4. Print the access token for you to copy to .env
"""

import argparse
import asyncio
import secrets
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ticktick_mcp.api.v1.auth import OAuth2Handler


# Configuration - UPDATE THESE VALUES
CLIENT_ID = os.environ.get("TICKTICK_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TICKTICK_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("TICKTICK_REDIRECT_URI", "http://127.0.0.1:8080/callback")

# Parse port from redirect URI
CALLBACK_PORT = int(urlparse(REDIRECT_URI).port or 8080)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle the OAuth callback."""

    authorization_code: str | None = None
    state: str | None = None
    error: str | None = None

    def do_GET(self):
        """Handle GET request (the OAuth callback)."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.authorization_code = params["code"][0]
            OAuthCallbackHandler.state = params.get("state", [None])[0]
            self._send_success_response()
        elif "error" in params:
            OAuthCallbackHandler.error = params.get("error_description", params["error"])[0]
            self._send_error_response()
        else:
            self._send_error_response("Unknown response")

    def _send_success_response(self):
        """Send success HTML response."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Authorization Successful</title></head>
        <body style="font-family: system-ui; text-align: center; padding: 50px;">
            <h1 style="color: #22c55e;">Authorization Successful!</h1>
            <p>You can close this window and return to the terminal.</p>
            <p style="color: #666;">The access token will be displayed in your terminal.</p>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str = None):
        """Send error HTML response."""
        error_msg = error or OAuthCallbackHandler.error or "Unknown error"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Authorization Failed</title></head>
        <body style="font-family: system-ui; text-align: center; padding: 50px;">
            <h1 style="color: #ef4444;">Authorization Failed</h1>
            <p>{error_msg}</p>
            <p>Please try again.</p>
        </body>
        </html>
        """
        self.send_response(400)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


async def run_auto_mode(handler: OAuth2Handler, auth_url: str):
    """Run OAuth flow with automatic browser and local callback server."""
    print("Step 1: Opening browser for authorization...")
    print(f"\nIf the browser doesn't open, visit this URL manually:\n")
    print(f"  {auth_url}\n")

    # Start local server to receive callback
    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), OAuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    # Open browser
    webbrowser.open(auth_url)

    print(f"Step 2: Waiting for callback on port {CALLBACK_PORT}...")
    print("        (Authorize the app in your browser)\n")

    # Wait for callback
    while OAuthCallbackHandler.authorization_code is None and OAuthCallbackHandler.error is None:
        server.handle_request()

    server.server_close()

    if OAuthCallbackHandler.error:
        print(f"ERROR: Authorization failed: {OAuthCallbackHandler.error}")
        return None

    return OAuthCallbackHandler.authorization_code


async def run_manual_mode(handler: OAuth2Handler, auth_url: str):
    """Run OAuth flow manually (SSH-friendly)."""
    print("=" * 70)
    print("  STEP 1: Open this URL in ANY browser (phone, tablet, other computer)")
    print("=" * 70)
    print()
    print(auth_url)
    print()
    print("=" * 70)
    print()
    print("STEP 2: Authorize the app when prompted")
    print()
    print("STEP 3: After authorizing, you'll be redirected to a URL like:")
    print("        http://127.0.0.1:8080/callback?code=XXXXX&state=YYYYY")
    print()
    print("        (The page will show an error - that's OK!)")
    print("        Copy the 'code' value from that URL.")
    print()
    print("=" * 70)
    print()

    code = input("Paste the 'code' here: ").strip()

    if not code:
        print("ERROR: No code provided")
        return None

    # Clean up the code if they pasted more than just the code
    if "code=" in code:
        # They pasted the full URL or query string
        parsed = parse_qs(code.split("?")[-1] if "?" in code else code)
        if "code" in parsed:
            code = parsed["code"][0]

    return code


async def main():
    """Run the OAuth2 flow."""
    parser = argparse.ArgumentParser(description="Get TickTick OAuth2 access token")
    parser.add_argument(
        "--manual", "-m",
        action="store_true",
        help="Manual mode: prints URL for you to visit (SSH-friendly)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  TickTick OAuth2 Token Acquisition")
    if args.manual:
        print("  (Manual Mode - SSH-friendly)")
    print("=" * 60 + "\n")

    # Check for credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Missing credentials!\n")
        print("Please set environment variables:")
        print("  export TICKTICK_CLIENT_ID='your_client_id'")
        print("  export TICKTICK_CLIENT_SECRET='your_client_secret'")
        print("\nOr create a .env file and source it:")
        print("  source .env")
        print("\nGet credentials from: https://developer.ticktick.com/manage")
        return

    print(f"Client ID: {CLIENT_ID[:8]}...{CLIENT_ID[-4:] if len(CLIENT_ID) > 8 else ''}")
    print(f"Redirect URI: {REDIRECT_URI}")
    print()

    # Create OAuth handler
    handler = OAuth2Handler(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
    )

    # Generate authorization URL
    auth_url, state = handler.get_authorization_url()

    # Get authorization code
    if args.manual:
        code = await run_manual_mode(handler, auth_url)
    else:
        code = await run_auto_mode(handler, auth_url)

    if not code:
        print("ERROR: No authorization code received")
        return

    print("\nExchanging authorization code for access token...")

    # Exchange code for token
    try:
        token = await handler.exchange_code(code=code, state=None)
    except Exception as e:
        print(f"\nERROR: Token exchange failed: {e}")
        return

    print("\n" + "=" * 60)
    print("  SUCCESS! Here is your access token:")
    print("=" * 60)
    print(f"\n{token.access_token}\n")
    print("=" * 60)

    print("\nAdd this to your .env file:")
    print(f"\n  TICKTICK_ACCESS_TOKEN={token.access_token}\n")

    if token.expires_in:
        hours = token.expires_in / 3600
        print(f"Note: This token expires in {hours:.1f} hours ({token.expires_in} seconds)")
    else:
        print("Note: Token expiration not specified (may be long-lived)")

    if token.refresh_token:
        print(f"\nRefresh token (save this for later):\n  {token.refresh_token}")

    print()


if __name__ == "__main__":
    asyncio.run(main())

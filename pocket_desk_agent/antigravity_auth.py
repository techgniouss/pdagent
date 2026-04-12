"""Antigravity OAuth authentication implementation."""

import os
import json
import base64
import webbrowser
import time
import secrets
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional, Callable, Tuple
from urllib.parse import urlparse, parse_qs, urlencode
import requests
import logging

from pocket_desk_agent.constants import (
    OAUTH_REDIRECT_URI,
    ANTIGRAVITY_SCOPES,
    ANTIGRAVITY_ENDPOINT_DAILY,
    ANTIGRAVITY_ENDPOINT_PROD,
    GEMINI_CLI_HEADERS,
    ANTIGRAVITY_HEADERS,
    DEFAULT_OAUTH_CLIENT_ID,
    DEFAULT_OAUTH_CLIENT_SECRET,
)

logger = logging.getLogger(__name__)

# OAuth Configuration — env vars override the built-in Gemini CLI defaults.
OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID") or DEFAULT_OAUTH_CLIENT_ID
OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or DEFAULT_OAUTH_CLIENT_SECRET


class TokenStorage:
    """Manages token storage and retrieval"""
    
    def __init__(self, app_name: str = "antigravity-chatbot"):
        self.config_dir = Path.home() / ".config" / app_name
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.tokens_file = self.config_dir / "tokens.json"
    
    def save_tokens(self, tokens: dict) -> None:
        """Save tokens to file with restricted permissions."""
        with open(self.tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        # Restrict file permissions so other users cannot read tokens
        try:
            if os.name != "nt":
                os.chmod(self.tokens_file, 0o600)
            else:
                # Windows: use icacls to restrict access to current user only.
                # Steps: remove inherited permissions, then grant R/W to current user.
                import subprocess
                username = os.getenv("USERNAME", "")
                if username:
                    result = subprocess.run(
                        ["icacls", str(self.tokens_file), "/inheritance:r",
                         "/grant:r", f"{username}:(R,W)"],
                        capture_output=True, text=True, check=False,
                    )
                    if result.returncode != 0:
                        logger.warning(
                            f"Could not restrict token file permissions: "
                            f"{result.stderr.strip() or result.stdout.strip()}"
                        )
                else:
                    logger.warning(
                        "Could not restrict token file permissions: "
                        "USERNAME environment variable not set."
                    )
        except Exception as exc:
            logger.warning(f"Could not restrict token file permissions: {exc}")
    
    def load_tokens(self) -> Optional[dict]:
        """Load tokens from file"""
        if self.tokens_file.exists():
            with open(self.tokens_file, 'r') as f:
                return json.load(f)
        return None
    
    def clear_tokens(self) -> None:
        """Clear stored tokens"""
        if self.tokens_file.exists():
            self.tokens_file.unlink()


class PKCEGenerator:
    """Generates PKCE code verifier and challenge"""
    
    @staticmethod
    def generate() -> Tuple[str, str]:
        """Generate PKCE verifier and challenge"""
        verifier = secrets.token_urlsafe(64)[:128]
        challenge_bytes = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=').decode('utf-8')
        return verifier, challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback.

    Class-level state is used because HTTPServer creates a new handler
    instance per request, so instance attributes cannot carry data back
    to the caller.  ``reset()`` must be called before each login flow.
    """

    auth_code: Optional[str] = None
    auth_state: Optional[str] = None
    callback_received = threading.Event()

    @classmethod
    def reset(cls) -> None:
        """Clear state for a new login flow."""
        cls.auth_code = None
        cls.auth_state = None
        cls.callback_received.clear()
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs"""
        pass
    
    def do_GET(self):
        """Handle GET request for OAuth callback"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/oauth-callback':
            query = parse_qs(parsed_url.query)
            
            if 'code' in query and 'state' in query:
                OAuthCallbackHandler.auth_code = query['code'][0]
                OAuthCallbackHandler.auth_state = query['state'][0]
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Successful</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                        }
                        .container {
                            text-align: center;
                            padding: 40px;
                            background: rgba(255,255,255,0.1);
                            border-radius: 20px;
                            backdrop-filter: blur(10px);
                        }
                        h1 { margin-bottom: 10px; }
                        p { opacity: 0.9; }
                        .checkmark { font-size: 60px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="checkmark">✓</div>
                        <h1>Authentication Successful!</h1>
                        <p>You can close this window and return to Telegram.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode('utf-8'))
                OAuthCallbackHandler.callback_received.set()
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Authentication Failed</h1></body></html>')
        else:
            self.send_response(404)
            self.end_headers()


class AntigravityOAuth:
    """Handles OAuth flow for Antigravity/Google authentication"""
    
    def __init__(self, on_status_update: Optional[Callable[[str], None]] = None):
        self.storage = TokenStorage()
        self.on_status_update = on_status_update or logger.info
        self.server: Optional[HTTPServer] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.email: Optional[str] = None
        self.project_id: Optional[str] = None
        self.expires_at: float = 0
    
    def _update_status(self, message: str):
        """Update status callback"""
        self.on_status_update(message)
    
    def _encode_state(self, verifier: str, project_id: str = "") -> str:
        """Encode state parameter with verifier and project ID"""
        payload = {"verifier": verifier, "projectId": project_id}
        return base64.urlsafe_b64encode(
            json.dumps(payload).encode('utf-8')
        ).decode('utf-8').rstrip('=')
    
    def _decode_state(self, state: str) -> Tuple[str, str]:
        """Decode state parameter to extract verifier and project ID"""
        padding = 4 - len(state) % 4
        if padding != 4:
            state += '=' * padding
        
        decoded = base64.urlsafe_b64decode(state).decode('utf-8')
        data = json.loads(decoded)
        return data.get('verifier', ''), data.get('projectId', '')
    
    def build_authorization_url(self) -> Tuple[str, str]:
        """Build the OAuth authorization URL with PKCE"""
        verifier, challenge = PKCEGenerator.generate()
        state = self._encode_state(verifier)
        
        params = {
            'client_id': OAUTH_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': OAUTH_REDIRECT_URI,
            'scope': ' '.join(ANTIGRAVITY_SCOPES),
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return auth_url, verifier
    
    def start_callback_server(self) -> None:
        """Start local HTTP server to receive OAuth callback"""
        OAuthCallbackHandler.reset()
        
        self.server = HTTPServer(('localhost', 51121), OAuthCallbackHandler)
        
        def serve():
            while not OAuthCallbackHandler.callback_received.is_set():
                self.server.handle_request()
        
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
    
    def stop_callback_server(self) -> None:
        """Stop the callback server"""
        if self.server:
            self.server.server_close()
            self.server = None
    
    def exchange_code(self, code: str, verifier: str) -> bool:
        """Exchange authorization code for access and refresh tokens"""
        self._update_status("Exchanging authorization code...")
        
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Accept": "*/*",
                    **GEMINI_CLI_HEADERS,
                },
                data={
                    'client_id': OAUTH_CLIENT_ID,
                    'client_secret': OAUTH_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': OAUTH_REDIRECT_URI,
                    'code_verifier': verifier,
                },
                timeout=30
            )
            
            if not response.ok:
                self._update_status(f"Token exchange failed: {response.text}")
                return False
            
            data = response.json()
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            self.expires_at = time.time() + data.get('expires_in', 3600)
            
            self._fetch_user_info()
            self._fetch_project_id()
            self._save_tokens()
            
            self._update_status(f"Authenticated as {self.email or 'Unknown'} (Project: {self.project_id})")
            return True
            
        except Exception as e:
            self._update_status(f"Token exchange error: {str(e)}")
            return False
    
    def _fetch_user_info(self) -> None:
        """Fetch user email from Google OAuth userinfo endpoint"""
        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    **GEMINI_CLI_HEADERS,
                },
                timeout=10
            )
            if response.ok:
                data = response.json()
                self.email = data.get('email')
        except Exception:
            pass
    
    def _fetch_project_id(self) -> None:
        """Fetch project ID from Antigravity API - matching working implementation"""
        manual_project = os.getenv("GOOGLE_PROJECT_ID") or os.getenv("ANTIGRAVITY_PROJECT_ID")
        if manual_project:
            self.project_id = manual_project
            return

        endpoints = [ANTIGRAVITY_ENDPOINT_PROD, ANTIGRAVITY_ENDPOINT_DAILY]
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    f"{endpoint}/v1internal:loadCodeAssist",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                        **GEMINI_CLI_HEADERS,
                        "Client-Metadata": ANTIGRAVITY_HEADERS["Client-Metadata"],
                    },
                    json={
                        "metadata": {
                            "ideType": "IDE_UNSPECIFIED",
                            "platform": "PLATFORM_UNSPECIFIED",
                            "pluginType": "GEMINI",
                        }
                    },
                    timeout=10
                )
                
                if response.ok:
                    data = response.json()
                    project = data.get('cloudaicompanionProject', {})
                    if isinstance(project, str):
                        self.project_id = project
                    elif isinstance(project, dict):
                        self.project_id = project.get('id', '')
                    
                    if self.project_id:
                        self._update_status(f"Fetched project ID: {self.project_id}")
                        return
            except Exception as e:
                self._update_status(f"Error fetching project from {endpoint}: {e}")
                continue
        
        # No fallback — require explicit configuration
        if not self.project_id:
            self._update_status(
                "Could not determine Google Cloud project ID. "
                "Set GOOGLE_PROJECT_ID in your config or .env file."
            )
    
    def _save_tokens(self) -> None:
        """Save tokens to persistent storage"""
        self.storage.save_tokens({
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.expires_at,
            'email': self.email,
            'project_id': self.project_id,
        })
    
    def load_saved_tokens(self) -> bool:
        """Load and validate saved tokens"""
        tokens = self.storage.load_tokens()
        if not tokens:
            return False
        
        self.access_token = tokens.get('access_token')
        self.refresh_token = tokens.get('refresh_token')
        self.expires_at = tokens.get('expires_at', 0)
        self.email = tokens.get('email')
        self.project_id = tokens.get('project_id')
        
        if time.time() >= self.expires_at - 60:
            return self.refresh_access_token()
        
        return bool(self.access_token)
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            return False
        
        self._update_status("Refreshing access token...")
        
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    **GEMINI_CLI_HEADERS,
                },
                data={
                    'client_id': OAUTH_CLIENT_ID,
                    'client_secret': OAUTH_CLIENT_SECRET,
                    'refresh_token': self.refresh_token,
                    'grant_type': 'refresh_token',
                },
                timeout=30
            )
            
            if response.ok:
                data = response.json()
                self.access_token = data.get('access_token')
                self.expires_at = time.time() + data.get('expires_in', 3600)
                # Re-fetch project ID on every token refresh to avoid stale/wrong project
                self._fetch_project_id()
                self._save_tokens()
                self._update_status("Token refreshed successfully")
                return True
            else:
                self._update_status(f"Token refresh failed: {response.text}")
                return False
                
        except Exception as e:
            self._update_status(f"Token refresh error: {str(e)}")
            return False
    
    def ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token, refreshing if needed"""
        if time.time() >= self.expires_at - 60:
            return self.refresh_access_token()
        return bool(self.access_token)
    
    def logout(self) -> None:
        """Clear all stored tokens"""
        self.storage.clear_tokens()
        self.access_token = None
        self.refresh_token = None
        self.email = None
        self.project_id = None
        self.expires_at = 0
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return bool(self.access_token) and time.time() < self.expires_at
    
    def start_login_flow(self) -> bool:
        """Start the complete OAuth login flow"""
        self._update_status("Starting authentication...")
        try:
            auth_url, verifier = self.build_authorization_url()
            self.start_callback_server()
            
            self._update_status("Opening browser for authentication...")
            webbrowser.open(auth_url)
            
            OAuthCallbackHandler.callback_received.wait(timeout=300)
            
            if OAuthCallbackHandler.auth_code:
                return self.exchange_code(OAuthCallbackHandler.auth_code, verifier)
            else:
                self._update_status("Authentication timed out or was cancelled")
                return False
        finally:
            self.stop_callback_server()

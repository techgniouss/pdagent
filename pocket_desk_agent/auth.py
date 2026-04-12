"""Authentication module with antigravity integration."""

import logging
from typing import Optional, Dict
from telegram import Update

from pocket_desk_agent.config import Config
from pocket_desk_agent.antigravity_auth import AntigravityOAuth

logger = logging.getLogger(__name__)


class AntigravityAuth:
    """Handles antigravity authentication for multiple users."""
    
    def __init__(self):
        # Store OAuth instances per user
        self.user_oauth_instances: Dict[int, AntigravityOAuth] = {}
    
    def _get_oauth_instance(self, user_id: int) -> AntigravityOAuth:
        """Get or create OAuth instance for user."""
        if user_id not in self.user_oauth_instances:
            def status_callback(msg: str):
                logger.info(f"[User {user_id}] {msg}")
            
            self.user_oauth_instances[user_id] = AntigravityOAuth(
                on_status_update=status_callback
            )
        return self.user_oauth_instances[user_id]
    
    def is_authenticated(self, user_id: int) -> bool:
        """Check if user is authenticated."""
        if user_id not in self.user_oauth_instances:
            # Try to load saved tokens
            oauth = self._get_oauth_instance(user_id)
            return oauth.load_saved_tokens()
        
        oauth = self.user_oauth_instances[user_id]
        return oauth.is_authenticated()
    
    def get_user_info(self, user_id: int) -> Optional[dict]:
        """Get authenticated user info."""
        oauth = self._get_oauth_instance(user_id)
        
        if not oauth.is_authenticated():
            # Try to load tokens
            if not oauth.load_saved_tokens():
                return None
        
        return {
            'email': oauth.email,
            'project_id': oauth.project_id,
            'access_token': oauth.access_token,
        }
    
    def logout_user(self, user_id: int):
        """Logout user."""
        if user_id in self.user_oauth_instances:
            oauth = self.user_oauth_instances[user_id]
            oauth.logout()
            del self.user_oauth_instances[user_id]
            logger.info(f"User {user_id} logged out")


def is_user_allowed(update: Update) -> bool:
    """Check if user is in allowed list."""
    if not update.effective_user:
        return False
    return update.effective_user.id in Config.AUTHORIZED_USER_IDS

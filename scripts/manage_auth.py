#!/usr/bin/env python3
"""
Pocket Desk Agent Authentication Manager
CLI tool for managing Gemini authentication tokens on the local machine
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def manage_auth():
    """Interactive authentication manager"""
    from pocket_desk_agent.config import Config
    from pocket_desk_agent.constants import AUTH_MODE_GEMINI_CLI, AUTH_MODE_APIKEY

    if Config.GEMINI_AUTH_MODE == AUTH_MODE_APIKEY:
        print("Bot is configured to use API Key. Authentication via OAuth is not needed.")
        return

    if Config.GEMINI_AUTH_MODE == AUTH_MODE_GEMINI_CLI:
        from pocket_desk_agent.gemini_cli_auth import GeminiCLIOAuth
        oauth = GeminiCLIOAuth()
        mode_name = "Gemini CLI OAuth"
    else:
        from pocket_desk_agent.antigravity_auth import AntigravityOAuth
        oauth = AntigravityOAuth()
        mode_name = "Antigravity OAuth"

    print("=" * 50)
    print(f"POCKET DESK AGENT AUTHENTICATION ({mode_name})")
    print("=" * 50)
    print("\n1. Login (Authenticate)")
    print("2. Logout (Clear Tokens)")
    print("3. Check Status")
    print("4. Refresh Token")
    print("5. Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    tokens_file = oauth.storage.tokens_file
    
    if choice == "1":
        print("\n" + "=" * 50)
        print("STARTING LOGIN FLOW")
        print("=" * 50)
        print(f"\nThis will open your browser for {mode_name} authentication.")
        print("Make sure you're running this on a machine with a browser.")
        input("\nPress Enter to continue...")
        
        success = oauth.start_login_flow()
        
        if success and oauth.is_authenticated():
            print("\n" + "=" * 50)
            print("✅ LOGIN SUCCESSFUL")
            print("=" * 50)
            print(f"Email: {oauth.email}")
            if getattr(oauth, 'project_id', None):
                print(f"Project ID: {oauth.project_id}")
            print(f"Tokens saved to: {tokens_file}")
            print("\nYou can now use the Telegram bot!")
        else:
            print("\n" + "=" * 50)
            print("❌ LOGIN FAILED")
            print("=" * 50)
            print("Please try again or check the logs for errors.")
        
    elif choice == "2":
        oauth.logout()
        print("\n" + "=" * 50)
        print("✅ LOGOUT COMPLETE")
        print("=" * 50)
        print("All tokens have been cleared.")
        print(f"Deleted: {tokens_file}")
            
    elif choice == "3":
        print("\n" + "=" * 50)
        print("AUTHENTICATION STATUS")
        print("=" * 50)
        
        if oauth.load_saved_tokens():
            print(f"\n✅ Authenticated")
            print(f"Email: {oauth.email}")
            if getattr(oauth, 'project_id', None):
                print(f"Project ID: {oauth.project_id}")
            print(f"Token expires: {time.ctime(oauth.expires_at)}")
            print(f"Valid: {'Yes' if oauth.is_authenticated() else 'No (expired)'}")
            print(f"Tokens file: {tokens_file}")
        else:
            print("\n❌ Not Authenticated")
            print("No valid tokens found.")
            print(f"Expected location: {tokens_file}")
            print("\nRun option 1 to login.")
    
    elif choice == "4":
        print("\n" + "=" * 50)
        print("REFRESHING TOKEN")
        print("=" * 50)
        
        if oauth.load_saved_tokens():
            if oauth.refresh_access_token():
                print("\n✅ Token Refreshed Successfully")
                print(f"New expiry: {time.ctime(oauth.expires_at)}")
            else:
                print("\n❌ Token Refresh Failed")
                print("You may need to login again (option 1).")
        else:
            print("\n❌ No tokens to refresh")
            print("Please login first (option 1).")
    
    elif choice == "5":
        print("\nGoodbye!")
        sys.exit(0)
    
    else:
        print("\n❌ Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    try:
        manage_auth()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

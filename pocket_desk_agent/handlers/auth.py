"""Authentication command handlers (login, authcode, checkauth, logout)."""

import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pocket_desk_agent.handlers._shared import (
    auth_client,
    gemini_client,
)

logger = logging.getLogger(__name__)

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command - generate OAuth link for mobile authentication."""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id

    # Check if already authenticated
    if auth_client.is_authenticated(user_id):
        user_info = auth_client.get_user_info(user_id)
        await update.message.reply_text(
            f"✅ You're already authenticated!\n\n"
            f"Email: {user_info.get('email', 'Unknown')}\n"
            f"Project: {user_info.get('project_id', 'Unknown')}\n\n"
            f"Use /logout to sign out."
        )
        return
    
    await update.message.reply_text(
        "🔐 Generating authentication link...\n\n"
        "Please wait..."
    )
    
    try:
        # Get OAuth instance for this user
        oauth = auth_client._get_oauth_instance(user_id)
        
        # Build authorization URL
        auth_url, verifier = oauth.build_authorization_url()
        
        # Store verifier for later use
        if not hasattr(auth_client, '_pending_verifiers'):
            auth_client._pending_verifiers = {}
        auth_client._pending_verifiers[user_id] = verifier
        
        await update.message.reply_text(
            f"🔗 Authentication Link:\n\n"
            f"{auth_url}\n\n"
            f"📱 Instructions:\n"
            f"1. Open the link above on ANY device (mobile/desktop)\n"
            f"2. Sign in with your Google account\n"
            f"3. Grant the requested permissions\n"
            f"4. You'll see a page with an authorization code\n"
            f"5. Copy the ENTIRE code\n"
            f"6. Send it back here using: /authcode <code>\n\n"
            f"⏰ Link expires in 10 minutes\n\n"
            f"💡 Tip: The code will be a long string of letters and numbers"
        )
        logger.info(f"Generated auth link for user {user_id}")
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error generating authentication link: {str(e)}"
        )
        logger.error(f"Error in login_command: {e}", exc_info=True)


async def authcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /authcode command - process authorization code from user."""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id

    # Check if already authenticated
    if auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "✅ You're already authenticated!\n\n"
            "Use /logout to sign out first if you want to re-authenticate."
        )
        return
    
    # Get authorization code from arguments
    if not context.args:
        await update.message.reply_text(
            "Usage: /authcode <authorization_code>\n\n"
            "Example:\n"
            "/authcode 4/0AanRRrtT...\n\n"
            "Get your authorization code by:\n"
            "1. Use /login to get the authentication link\n"
            "2. Complete the OAuth flow\n"
            "3. Copy the authorization code\n"
            "4. Send it here with /authcode"
        )
        return
    
    auth_code = " ".join(context.args).strip()
    
    # Check if we have a pending verifier for this user
    if not hasattr(auth_client, '_pending_verifiers') or user_id not in auth_client._pending_verifiers:
        await update.message.reply_text(
            "❌ No pending authentication found.\n\n"
            "Please use /login first to start the authentication process."
        )
        return
    
    verifier = auth_client._pending_verifiers[user_id]
    
    await update.message.reply_text(
        "🔄 Processing authorization code...\n\n"
        "Please wait..."
    )
    
    try:
        # Get OAuth instance
        oauth = auth_client._get_oauth_instance(user_id)
        
        # Exchange code for tokens
        success = oauth.exchange_code(auth_code, verifier)
        
        if success:
            # Clear pending verifier
            del auth_client._pending_verifiers[user_id]
            
            user_info = auth_client.get_user_info(user_id)
            await update.message.reply_text(
                f"✅ Authentication successful!\n\n"
                f"Email: {user_info.get('email', 'Unknown')}\n"
                f"Project: {user_info.get('project_id', 'Unknown')}\n\n"
                f"You can now use all bot features!\n"
                f"Try /help to see available commands."
            )
            logger.info(f"User {user_id} authenticated successfully via authcode")
        else:
            await update.message.reply_text(
                "❌ Authentication failed.\n\n"
                "Possible reasons:\n"
                "• Invalid or expired authorization code\n"
                "• Code already used\n"
                "• Network error\n\n"
                "Please try /login again to get a new link."
            )
            logger.error(f"Failed to exchange auth code for user {user_id}")
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error processing authorization code: {str(e)}\n\n"
            "Please try /login again."
        )
        logger.error(f"Error in authcode_command: {e}", exc_info=True)


async def checkauth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /checkauth command - check if authentication was completed."""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id

    # Check if user is now authenticated
    if auth_client.is_authenticated(user_id):
        user_info = auth_client.get_user_info(user_id)
        await update.message.reply_text(
            f"✅ Authentication successful!\n\n"
            f"Email: {user_info.get('email', 'Unknown')}\n"
            f"Project: {user_info.get('project_id', 'Unknown')}\n\n"
            f"You can now use all bot features!\n"
            f"Try /help to see available commands."
        )
        logger.info(f"User {user_id} authentication verified")
    else:
        await update.message.reply_text(
            "⏳ Authentication not completed yet.\n\n"
            "Please complete the authentication process:\n"
            "1. Use /login to get your authentication link\n"
            "2. Open the link and sign in\n"
            "3. Come back and use /checkauth again\n\n"
            "If you've already completed authentication, please wait a moment and try again."
        )
        logger.info(f"User {user_id} authentication check - not authenticated")


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /logout command - clear authentication."""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id

    # Check if user is authenticated
    if not auth_client.is_authenticated(user_id):
        await update.message.reply_text(
            "ℹ️ You're not currently authenticated.\n\n"
            "Use /login to authenticate."
        )
        return
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, logout", callback_data="confirm_logout"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_logout")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Are you sure you want to logout?\n\n"
        "This will clear your authentication and you'll need to login again.",
        reply_markup=reply_markup
    )



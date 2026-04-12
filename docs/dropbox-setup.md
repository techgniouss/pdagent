# Dropbox Setup Guide

This guide explains how to configure Dropbox integration for uploading large APK files from the `/build` and `/getapk` workflow.

## Why Dropbox?

When an APK exceeds 50 MB, Telegram's file size limit is hit. The bot offers two upload options at that point:

- **TempFile** — fast, auto-deletes after one download or 14 days, max 100 MB
- **Dropbox** — permanent storage, unlimited size, shareable link

Dropbox is the right choice for files over 100 MB or files you want to keep.

> The `dropbox` Python library is included in the standard installation — no separate `pip install` is needed.

---

## Setup Steps

### 1. Create a Dropbox App

1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click **Create app**
3. Choose:
   - **API**: Scoped access
   - **Access type**: Full Dropbox (or App folder)
   - **App name**: Any name (e.g., `PocketDeskAgent`)
4. Click **Create app**

### 2. Set Permissions

> Do this **before** generating a token — tokens only inherit permissions that exist at generation time.

1. In your app settings, go to the **Permissions** tab
2. Enable these scopes:
   - `files.content.write`
   - `files.content.read`
   - `sharing.write`
3. Click **Submit**

### 3. Generate an Access Token

1. Go to the **Settings** tab
2. Scroll to **OAuth 2** → **Generated access token**
3. Click **Generate**
4. Copy the token (starts with `sl.`)

### 4. Add the Token to Your Config

Add this to your `.env` file or `~/.pdagent/config.ini`:

```ini
DROPBOX_ACCESS_TOKEN=sl.your_access_token_here
```

Then restart the bot:

```bash
pdagent restart
```

---

## File Organization

Uploaded files are stored at:

```
/PocketDeskAgent/<filename>.apk
```

Accessible from the Dropbox web interface, mobile app, or desktop client.

---

## Troubleshooting

**"missing_scope" or `AuthError`**
- You set permissions after generating the token. Generate a **new** token after saving permissions.

**"Dropbox not configured"**
- `DROPBOX_ACCESS_TOKEN` is missing from your config. Add it and restart the bot.

**"Invalid Dropbox access token"**
- The token may have expired or been revoked. Generate a new one from the App Console and update your config.

**Upload fails**
- Check your Dropbox storage quota.
- Verify the token has write permissions (see step 2 above).
- Check `bot.log` for detailed error output.

---

## Security Notes

- Keep your access token out of version control — never commit `.env`.
- The token grants full read/write access to your Dropbox. Revoke it from the App Console if compromised.

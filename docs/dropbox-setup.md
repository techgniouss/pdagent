# Dropbox Setup Guide

Use Dropbox when you want Pocket Desk Agent to upload large APK files to permanent cloud storage instead of using a temporary download service.

---

## When Dropbox Is Useful

Dropbox is the best option when:

- The APK is too large for Telegram
- The file exceeds the temporary upload limit
- You want a persistent download link or long-term storage

For large APK delivery, Pocket Desk Agent offers:

- `TempFile.org`: temporary hosting, no setup required, up to 100 MB
- `Dropbox`: persistent storage, requires configuration

---

## 1. Create a Dropbox App

1. Open the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click **Create app**
3. Choose:
   - **API**: Scoped access
   - **Access type**: Full Dropbox or App folder
   - **App name**: Any descriptive name, such as `PocketDeskAgent`
4. Finish creating the app

---

## 2. Grant Required Permissions

Enable these scopes in the **Permissions** tab before generating a token:

| Scope | Purpose |
| :--- | :--- |
| `files.content.write` | Upload APK files to your Dropbox |
| `files.content.read` | Verify uploads and read file metadata |
| `sharing.write` | Create shareable download links sent back to you via Telegram |

After selecting the scopes, click **Submit**.

> Tokens only inherit permissions that exist at the time they are generated. If you change scopes later, generate a new token.

---

## 3. Generate an Access Token

1. Open the **Settings** tab for your Dropbox app
2. Find **OAuth 2**
3. Generate an access token
4. Copy the token value

> **Token lifetime**: Tokens generated from the App Console are long-lived by default (they do not expire unless revoked). If you use a short-lived token via a custom OAuth flow, you will need to refresh it periodically. The long-lived token from the App Console is recommended for this integration.

---

## 4. Add the Token to Pocket Desk Agent

Add the token to `.env` or `~/.pdagent/config`:

```ini
DROPBOX_ACCESS_TOKEN=sl.your_access_token_here
```

Restart the bot after saving the token:

```bash
pdagent restart
```

---

## Storage Location

Uploaded APKs are stored in Dropbox under:

```text
/PocketDeskAgent/<filename>.apk
```

You can access them from the Dropbox web app, desktop client, or mobile app.

---

## Troubleshooting

### `missing_scope` or `AuthError`

- Regenerate the token after updating scopes
- Confirm the required Dropbox permissions were saved before token creation

### "Dropbox not configured"

- Add `DROPBOX_ACCESS_TOKEN` to your configuration
- Restart the bot after updating the configuration

### "Invalid Dropbox access token"

- Generate a fresh token in the Dropbox App Console
- Replace the old token in your config

### Upload fails

- Verify Dropbox storage space is available
- Confirm the token still has the required scopes
- Check `bot.log` for the detailed upload error

---

## Security Notes

- Never commit `DROPBOX_ACCESS_TOKEN` to version control
- Use an app-specific Dropbox token rather than reusing credentials from another integration
- **To revoke a token**: open the Dropbox App Console → your app → **Settings** → **OAuth 2** → click **Revoke** next to the generated token. Generate a fresh one afterward if needed.
- Revoke the token immediately if it is accidentally exposed (e.g., committed to a public repo)

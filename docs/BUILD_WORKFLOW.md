# Build Workflow Guide

## Overview

Pocket Desk Agent can start a React Native Android build from Telegram (via npm scripts), monitor the build, then locate and deliver the generated artifact.

> `/build` drives npm-script builds (React Native). `/getapk` retrieval works for **both** React Native (`android/`) and native Gradle/Kotlin (`app/`) projects — for native Kotlin projects, build with Android Studio / Gradle, then use `/getapk`.

Typical flow:

1. Scan your configured repository root for projects with a `package.json`
2. Let you choose a repository
3. Show available npm scripts, prioritizing Android build scripts
4. Run the selected build command
5. Report progress and completion status
6. Deliver the APK through Telegram or a large-file upload option

---

## Requirements

- Node.js and npm installed on the host machine
- Android build tools configured for the target project
- React Native repositories stored under `CLAUDE_DEFAULT_REPO_PATH`
- Optional: `DROPBOX_ACCESS_TOKEN` if you want Dropbox uploads for large APKs

> `DEFAULT_REPO_PATH` is still accepted as a legacy alias, but `CLAUDE_DEFAULT_REPO_PATH` is the documented setting going forward.

---

## Configuration

Set your repository root in `.env` or `~/.pdagent/config`:

```ini
CLAUDE_DEFAULT_REPO_PATH=C:\Users\YourName\Projects
```

Optional Dropbox configuration for large-file delivery:

```ini
DROPBOX_ACCESS_TOKEN=sl.your_access_token_here
UPLOAD_EXPIRY_TIME=1h
```

See [dropbox-setup.md](dropbox-setup.md) for the full Dropbox setup process.

---

## Workflow

### 1. Start the build flow

```text
/build
```

The bot scans the configured repository root and lists projects that contain a `package.json`.

### 2. Select a repository

Reply with either:

- A number such as `1` or `2`
- A repository name or partial name such as `MyApp`

### 3. Select a build script

The bot reads the selected `package.json` and shows available npm scripts. Scripts are ranked with Android-related ones first (those containing `android`, `build`, or `release` in their name), followed by all others alphabetically.

Reply with either:

- A number such as `1` or `2`
- A script name such as `android` or `android:release`

### 4. Monitor progress

The bot starts the build command and sends progress updates with recent output approximately every 30 seconds. When the command finishes, it reports success or failure along with the final build output.

### 5. Receive the APK

After a successful build, run `/getapk` and browse the build-outputs folder. The
browser auto-detects both project layouts:

- React Native / Capacitor / Cordova: `android/app/build/outputs/…`
- Native Gradle / Kotlin (Android Studio): `app/build/outputs/…`

> **APK and AAB:** Both `.apk` and `.aab` (Android App Bundle) artifacts are
> listed and can be delivered. Note that `.aab` files are for Play Store upload,
> not direct sideloading — install an `.apk` on a device.

> **Custom output paths:** If your project writes artifacts to a non-standard
> location, retrieve the file manually using `/find *.apk` or `/getfile <path>`.

`/getapk` reports the file name, size, and local path before sending or uploading it.

---

## APK Delivery Options

### Up to 50 MB

The bot sends the APK directly through Telegram as a document attachment.

### Over 50 MB

The bot presents upload choices:

- `TempFile.org`
  - No setup required
  - Maximum file size: 100 MB
  - Temporary hosted download link
  - Link expiry is controlled by `UPLOAD_EXPIRY_TIME`
- `Dropbox`
  - Requires `DROPBOX_ACCESS_TOKEN`
  - Suitable for larger files and permanent storage

### Over 100 MB

`TempFile.org` is not available. Use Dropbox instead.

---

## Example

```text
You: /build

Bot: Found 3 repositories.
     Reply with the number or name to select one.

You: 2

Bot: Selected: HomePay
     Available npm scripts:
     1. android
     2. android:release
     3. build:android

You: 2

Bot: Starting build...
     Repository: HomePay
     Command: npm run android:release

Bot: Build in progress...
     Recent output:
     > Task :app:bundleReleaseJsAndAssets
     > Task :app:compileReleaseJavaWithJavac

Bot: Build completed successfully.
     Found APK file:
     File: app-release.apk
     Size: 65.8 MB

Bot: Choose upload method:
     [TempFile (Auto-delete)]
     [Dropbox (Permanent)]
```

---

## Troubleshooting

### No repositories found

- Confirm `CLAUDE_DEFAULT_REPO_PATH` points to the correct root directory
- Verify the directory exists and is readable
- Make sure each target repository contains a `package.json`
- For **monorepos or nested workspaces**: the bot scans one level deep from `CLAUDE_DEFAULT_REPO_PATH`. If your projects are nested further, set `CLAUDE_DEFAULT_REPO_PATH` to the subdirectory that directly contains them, or use `/cd <path>` to switch the bot's working directory for the current session

### Build fails

- Review the error output sent by the bot
- Confirm project dependencies are installed
- Verify Android SDK, Java, Gradle, and signing configuration as required by the project
- Run the same npm script locally to confirm the failure is not project-specific

### APK not found

- Check the build output for the actual output directory
- Confirm the build script produces an APK rather than only an AAB
- Retrieve the artifact manually if your project uses a custom output path

### Large-file upload issues

- Files above 100 MB require Dropbox
- If Dropbox is selected, confirm `DROPBOX_ACCESS_TOKEN` is configured
- If TempFile.org fails, retry or use Dropbox instead

---

## Security

The build workflow executes npm scripts from repositories on your machine. Only use it with repositories and build commands you trust.

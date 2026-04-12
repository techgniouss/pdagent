# Build Workflow Guide

## Overview

The build workflow feature allows you to remotely build React Native Android apps from your Telegram bot. The bot will:

1. List all local repositories with `package.json`
2. Show available npm scripts from the selected repository
3. Execute the build command in a command prompt
4. Monitor the build progress and send updates
5. Find the generated APK file
6. Send the APK file back to you via Telegram

## Prerequisites

- Node.js and npm installed on your laptop
- React Native projects set up with Android build configuration
- Repositories located in the path specified by `DEFAULT_REPO_PATH` in your `.env` file

## Usage

### Step 1: Start the Build Workflow

Send the command:
```
/build
```

The bot will scan your `DEFAULT_REPO_PATH` directory and list all repositories that contain a `package.json` file.

### Step 2: Select a Repository

Reply with either:
- **Number**: `1`, `2`, `3`, etc.
- **Name**: `MyApp`, `HomePay`, etc. (partial match works)

Example:
```
1
```
or
```
MyApp
```

The bot will read the `package.json` and show you all available npm scripts, with priority given to build-related scripts (containing keywords like `android`, `build`, `release`, `debug`).

### Step 3: Select a Build Script

Reply with either:
- **Number**: `1`, `2`, `3`, etc.
- **Script name**: `android`, `build:android`, etc. (partial match works)

Example:
```
2
```
or
```
android
```

### Step 4: Monitor Build Progress

The bot will:
- Start the build process in a command prompt window
- Send you periodic updates every 30 seconds with recent output
- Notify you when the build completes (success or failure)

### Step 5: Receive the APK

If the build is successful, the bot will:
- Search for the APK file in standard locations:
  - `android/app/build/outputs/apk/debug/`
  - `android/app/build/outputs/apk/release/`
- Show you the file name and size
- Upload and send the APK file to you via Telegram

**Note**: Telegram has a 50 MB file size limit for bots. If your APK is larger, the bot will provide the file path for manual retrieval.

## APK File Handling

The bot automatically handles APK files based on their size:

### Small APKs (< 50 MB)
- Uploaded directly to Telegram
- Sent as a document attachment
- Can be downloaded immediately

### Large APKs (≥ 50 MB)
- Automatically uploaded to **file.io** (temporary file sharing)
- You receive a download link
- **Important**: Link expires after first download or 14 days
- Download immediately to avoid expiration

**Note**: Telegram has a 50 MB file size limit for bots. For larger files, we use file.io for temporary hosting.

## Configuration

Update your `.env` file with the path to your repositories:

```env
DEFAULT_REPO_PATH=C:\Users\YourName\Projects
```

## Example Workflow

```
You: /build

Bot: 🔨 Starting build workflow...
     
     📱 Found 3 React Native repositories:
     
     1. MyDigitalStudio
     2. HomePay
     3. GigsJobsSwipe
     
     💡 Reply with the number or name to select a repository.

You: 2

Bot: ✅ Selected: HomePay
     
     📋 Available npm scripts:
     
     1. npm run android
        → react-native run-android
     
     2. npm run android:release
        → cd android && ./gradlew assembleRelease
     
     3. npm run build:android
        → cd android && ./gradlew clean && ./gradlew assembleDebug
     
     💡 Reply with the number or script name to execute.

You: 2

Bot: 🚀 Starting build...
     
     Repository: HomePay
     Command: npm run android:release
     
     This may take several minutes. I'll send you updates...

Bot: ⏳ Build in progress...
     
     Recent output:
     ```
     > Task :app:bundleReleaseJsAndAssets
     > Task :app:compileReleaseJavaWithJavac
     ```

Bot: ✅ Build completed successfully!
     
     Searching for APK file...

Bot: 📦 Found APK file!
     
     File: app-release.apk
     Size: 28.5 MB
     Path: C:\Users\...\android\app\build\outputs\apk\release\app-release.apk
     
     Uploading to Telegram...

Bot: [Sends APK file as document]
     
     ✅ Build workflow completed!
     
     APK file sent successfully.
```

### Example: Large APK (>50 MB)

```
You: /build
You: 2
You: android:release

Bot: 🚀 Starting build...
     [Build completes]

Bot: 📦 Found APK file!
     
     File: app-release.apk
     Size: 65.8 MB
     
     ⚠️ APK file is too large (65.8 MB) for Telegram (max 50 MB).
     
     ☁️ Uploading to file.io for temporary download...

Bot: ✅ Upload successful!
     
     📥 Download your APK:
     https://file.io/abc123xyz
     
     ⚠️ Important:
     • Link expires after first download
     • Or after 14 days if not downloaded
     • Download it now to your phone/computer
     
     💡 Tip: Open the link on your Android device to install directly!
     
     📂 Local path (if needed):
     C:\Users\...\app-release.apk
```

## Troubleshooting

### No repositories found
- Check that `DEFAULT_REPO_PATH` is set correctly in `.env`
- Ensure your repositories have a `package.json` file
- Verify the path exists and is accessible

### Build fails
- Check the error output provided by the bot
- Ensure all dependencies are installed (`npm install`)
- Verify Android SDK and build tools are properly configured
- Check that the build script works when run manually

### APK not found
- The bot searches in standard React Native output locations
- If your project has a custom output path, you may need to retrieve the APK manually
- Check the build output for the actual APK location

### File too large
- Telegram bots can only send files up to 50 MB
- For larger APKs, the bot automatically uploads to **file.io**
- You'll receive a download link (expires after first download or 14 days)
- Download immediately to avoid expiration
- Consider enabling ProGuard/R8 to reduce APK size for future builds

## Tips

- Use debug builds for faster compilation during development
- Release builds take longer but produce optimized APKs
- The build process runs in the background - you can continue using your laptop
- Build state expires after 10 minutes of inactivity

## Security Note

The build workflow executes npm scripts from your repositories. Only use this feature with repositories you trust, as malicious scripts could be executed on your laptop.

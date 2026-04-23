# Live Remote Desktop (`/remote`)

Live browser-based remote control of the PC running `pdagent`. One Telegram
command returns a public HTTPS URL. Open it on your phone. You get a live
MJPEG stream of the desktop plus mouse + keyboard input from the browser.

No desktop client. No account at any third-party service. Works over mobile
data — the stream does NOT require the phone and PC to be on the same network.

---

## What it does

```
Telegram  ──/remote──▶  pdagent
                         ├── starts local aiohttp server on 127.0.0.1:<free port>
                         ├── spawns cloudflared quick-tunnel to that port
                         └── returns https://<random>.trycloudflare.com + QR

Phone browser ──https──▶ cloudflared ──ws──▶ aiohttp
                                             ├── frames   ─▶  mss/PIL/JPEG  (2–20 fps)
                                             └── input    ─▶  pyautogui     (mouse/keys)
```

- MJPEG-over-WebSocket video, separate WebSocket for input.
- xxhash thumbnail frame-diff — idle CPU drops to ~1 % when the screen is static.
- Adaptive quality via the in-viewer slider; adaptive FPS is clamped 2..20.

---

## Prerequisites

| Requirement | Why | How |
| :--- | :--- | :--- |
| Windows 10 / 11 | `pyautogui`, `mss` | — |
| Python 3.11+ | runtime | — |
| `cloudflared` binary | outbound HTTPS tunnel | `winget install Cloudflare.cloudflared` |

`cloudflared` is **not bundled**. Install it once. Test with `cloudflared --version`.

Firewall: cloudflared opens an **outbound** connection to Cloudflare's edge. No
inbound ports are needed. Corporate firewalls that strip outbound HTTPS may
block this; an exception for `*.cloudflare.com` is enough.

If the binary lives outside `PATH`, point the config at it:

```ini
# ~/.pdagent/config
CLOUDFLARED_PATH = C:\tools\cloudflared\cloudflared.exe
```

---

## Quick start

1. In Telegram: `/remote`
2. Bot replies within 5–10 seconds with a message like:

   ```
   ✅ Remote desktop ready.
   Open: https://abcd-efgh-ijkl.trycloudflare.com
   ```

   and sends a QR-code photo you can scan from the phone's camera.
3. Open the URL on your phone. The viewer fills the screen with the live desktop.
4. Tap anywhere to left-click. Drag to move + click-drag. Long-press for
   right-click. Two-finger vertical swipe to scroll. Tap the `⌨︎ keys` button
   to bring up the keyboard.
5. When done, send `/stopremote` in Telegram (or just let the 15-minute idle
   timeout end the session).

Ask Gemini naturally if you prefer: *"open remote"*, *"let me control my pc
from my phone"*, *"share my screen"*. The AI replies with an inline-keyboard
approval button — it never starts the session directly.

---

## Mobile UX guide

| Gesture / Control | Action |
| :--- | :--- |
| Single tap | Left click |
| Drag | Mouse move + left button drag |
| Long-press (500 ms) | Right click at release point |
| `↗ right` button + tap | One-shot right click (explicit) |
| Two-finger vertical swipe | Mouse wheel scroll |
| `⌨︎ keys` button | Focus hidden input — type normally; Backspace/Enter/Tab/Esc/arrows supported |
| Quality slider | JPEG quality 30..85 (debounced 250 ms) |
| `✕ end` button | Close the viewer (the Telegram session keeps running until `/stopremote`) |

Desktop browsers also work — mouse move/click/scroll and keyboard events are
forwarded the same way.

---

## Configuration reference

All variables live in `~/.pdagent/config` (INI) or as environment variables.

| Variable | Default | Range | Purpose |
| :--- | :--- | :--- | :--- |
| `REMOTE_ENABLED` | `true` | bool | Master switch. When `false`, `/remote` replies with a "disabled" message and no tunnel is spawned. |
| `REMOTE_AI_TOOLS_ENABLED` | `true` | bool | When `false`, Gemini's natural-language shortcuts for starting/stopping remote are disabled. `/remote` still works. |
| `REMOTE_BIND_HOST` | `127.0.0.1` | host | Local bind for the aiohttp server. Leave as `127.0.0.1`; cloudflared is the only ingress. |
| `REMOTE_IDLE_TIMEOUT_SECS` | `900` | ≥ 60 | Auto-end after this many seconds of no input. |
| `REMOTE_DEFAULT_FPS` | `10` | 2..20 | Initial capture rate. |
| `REMOTE_JPEG_QUALITY` | `60` | 30..85 | Initial JPEG quality. |
| `REMOTE_MAX_WIDTH` | `1280` | 640..1920 | Downscale wider screens to this width before JPEG encode. |
| `CLOUDFLARED_PATH` | `""` | path | Override PATH lookup when the binary is not on `PATH`. |

Changes take effect on next bot start.

---

## Security model

| Layer | What it does |
| :--- | :--- |
| Telegram allowlist | Only `AUTHORIZED_USER_IDS` can even call `/remote`. `safe_command` enforces this before anything else runs. |
| Random token | `secrets.token_urlsafe(32)` — 256-bit — appears only in `?t=` on the initial HTML hit and in the httpOnly `pdremote` cookie the server sets. |
| Cookie binding | `/ws/video` and `/ws/input` require the cookie to equal the session token. The query token only works once; sharing the URL **after** it has been opened does not share the session. |
| Fingerprint | On first hit, `(User-Agent, sha256(remote IP))` is recorded. Later WS upgrades must match — a different phone or a second browser is rejected with 401. |
| Input rate limit | The server caps mouse/key events at 200/sec per session. Overflow is dropped. |
| Bind host | aiohttp binds `127.0.0.1`. cloudflared is the single ingress. |
| Teardown | `/stopremote`, idle timeout, or bot shutdown close both WebSockets, stop the aiohttp runner, kill cloudflared, and delete all session state. Stale tokens 404 afterwards. |
| AI safety | Gemini can only **request** a session via an inline-keyboard confirmation. It never starts or stops one directly and never sees the raw token. |

What a leaked URL can NOT do:

- It cannot bypass `AUTHORIZED_USER_IDS` — they control `/remote` creation in the first place.
- After the first browser has opened it, the token is tied to that phone; a second opener gets 401.
- After `/stopremote` or idle timeout, the URL is gone.

---

## Resource profile

Measured on a mid-range Windows laptop at defaults (10 fps, JPEG q 60, 1280 px):

| State | CPU | RAM delta | Notes |
| :--- | :--- | :--- | :--- |
| `/remote` never invoked | ~0 % | 0 MB | All heavy libs (aiohttp, mss, xxhash, qrcode) are lazy-imported. |
| Session up, screen idle | ~1 % | ~45 MB | Frame-diff skip keeps emission near zero while the screen is static. |
| Session up, continuous activity | 6–9 % | ~60 MB | mss BitBlt + JPEG encode. |

Tuning knobs when resources are tight:

- Drop `REMOTE_DEFAULT_FPS` to 5 — still usable for light interaction.
- Drop `REMOTE_MAX_WIDTH` to 960.
- Drop `REMOTE_JPEG_QUALITY` to 45 for smaller frames on slow links.

---

## Troubleshooting

**`cloudflared not found`**
- Install with `winget install Cloudflare.cloudflared`, or download from
  <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/>.
- If it is installed but not on `PATH`, set `CLOUDFLARED_PATH` in
  `~/.pdagent/config`.

**URL never arrives / times out after 25 s**
- Cloudflared's outbound HTTPS is blocked. Check corporate firewalls and
  proxies.
- Test manually: `cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate`
  — you should see a `trycloudflare.com` URL within a few seconds.

**Video shows but clicks/keys do nothing**
- `pyautogui` fail-safe: if the mouse ever hits a screen corner, it pauses.
  You will also see a yellow overlay in the viewer. Move the cursor away from
  the corner.
- Focus problems: clicks into an elevated (UAC) window or the Windows login
  screen are blocked by Windows — this is by design, not a bug.

**Session ends almost immediately**
- Check `REMOTE_IDLE_TIMEOUT_SECS`. If set very low (e.g. 60), brief pauses
  will end the session.

**High CPU**
- Drop FPS / max width / quality as described above.
- Confirm the frame-diff skip is working: leave the desktop static — CPU
  should fall to ~1 % within 2–3 seconds.

**Sharing the URL with someone else doesn't work**
- That is by design. The session binds to the first browser that opens it.
  Start a fresh `/remote` for a new recipient.

---

## Known limitations (v1)

- Audio is not streamed.
- File drag-and-drop between phone and PC is not supported.
- Clipboard sync between phone and PC is not automatic (use `/clipboard` /
  `/viewclipboard`).
- UAC prompts and the Windows login screen will not receive clicks (OS
  security boundary).
- Games with anti-cheat may refuse synthetic input.
- A single authorized user can have at most one active session at a time.

---

## How to disable

Set in `~/.pdagent/config`:

```ini
REMOTE_ENABLED = false
```

and restart the bot. `/remote` then replies with a "disabled" message and no
server or tunnel is ever spawned.

To disable only Gemini's natural-language shortcut (but keep `/remote`
working):

```ini
REMOTE_AI_TOOLS_ENABLED = false
```

# Smart Plug & Auto Battery Management

Keep your laptop battery healthy automatically. Pocket Desk Agent connects to a **Qubo Smart Plug 10A** via MQTT and manages charging on your behalf — turning the plug off when the battery is full and back on when it runs low.

No separate service or cloud bridge is needed. The MQTT client runs **embedded inside the bot process**.

---

## How It Works

```
Battery level crosses threshold
        │
        ▼
_battery_manager_loop() (every 5 min)
        │
        ├─ % ≥ high threshold AND charging  ──→  plug OFF
        └─ % ≤ low threshold AND discharging ──→  plug ON
                │
                ▼
        QuboClient (embedded MQTT)
                │
                ▼
        Qubo cloud → Smart Plug 10A (MQTT TLS 8883)
```

- The monitor polls every **5 minutes** by default (configurable down to 30 s).
- Actions are only sent when the state actually needs to change — no redundant MQTT commands.
- The plug's **physical confirmation** is awaited (up to 8 s) after every command.
- Enabled/disabled state and thresholds are **persisted to disk** (`~/.pdagent/autobattery.json`) and automatically resume after a bot restart.

---

## Setup

### 1. Get your Qubo credentials

You need the email address and password you use to log into the **Qubo app** (same account that controls your Smart Plug 10A).

### 2. Add credentials

**Option A — configuration wizard (recommended):**

```bash
pdagent configure
```

On a fresh setup, the `[3/3] Optional Settings` step offers to configure the smart plug. On an existing setup, pick **"Smart Plug & Auto Battery"** from the selective-update menu — it prompts for the Qubo username/password, device name, and battery thresholds, and writes them to `~/.pdagent/credentials` (username/password) and `~/.pdagent/config` (device name, thresholds).

**Option B — edit the config files directly:**

```ini
# ~/.pdagent/credentials
[default]
qubo_username = your-qubo-email@example.com
qubo_password = your-qubo-password

# ~/.pdagent/config
[smartplug]
qubo_device_name = Smart Plug 10A
```

**Option C — environment variables** (highest precedence — overrides the files above):

```ini
QUBO_USERNAME=your-qubo-email@example.com
QUBO_PASSWORD=your-qubo-password
QUBO_DEVICE_NAME=Smart Plug 10A
```

`QUBO_DEVICE_NAME` must exactly match the device name shown in the Qubo app. Default is `Smart Plug 10A`. The device UUID itself is never hard-coded — it's looked up live from your Qubo account's device list on every login. If your account has only one Qubo device, it's used automatically even if `QUBO_DEVICE_NAME` doesn't match.

### 3. (Optional) Override thresholds via environment

| Variable | Default | Effect |
| :--- | :---: | :--- |
| `BATTERY_HIGH_THRESHOLD` | `85` | Plug turns OFF above this % while charging |
| `BATTERY_LOW_THRESHOLD` | `15` | Plug turns ON below this % while not charging |
| `BATTERY_POLL_INTERVAL` | `300` | Seconds between battery checks (min 30) |

All three can also be changed at runtime with `/autobattery high`, `/autobattery low`, and `/autobattery interval` — no restart needed.

---

## Commands

### `/autobattery` — Auto battery manager

| Subcommand | Effect |
| :--- | :--- |
| `/autobattery on` | Enable the battery manager (validates credentials first) |
| `/autobattery off` | Disable it and disconnect the plug client |
| `/autobattery status` | Show enabled state, battery %, thresholds, and poll interval |
| `/autobattery high <n>` | Set the high threshold (plug OFF above n% while charging) |
| `/autobattery low <n>` | Set the low threshold (plug ON below n% while discharging) |
| `/autobattery interval <n>` | Set poll interval in seconds (minimum 30) |

**Example session:**

```
/autobattery on
✅ Auto battery manager enabled
• High threshold: 85% → plug will turn OFF
• Low threshold:  15% → plug will turn ON
• Polling every 300s

/autobattery high 90
✅ High threshold set to 90%.

/autobattery status
🔋 Auto Battery Manager
• Status: 🟢 ENABLED (running)
• Battery: 73% — 🔌 Charging
• High threshold: 90% (plug OFF above this while charging)
• Low threshold:  15% (plug ON below this while discharging)
• Poll interval: 300s (5m 0s)
```

Notifications are sent to Telegram automatically whenever the plug state changes:

```
🔋 Auto battery: smart plug turned OFF
• Reason: battery at 90% while charging
• Status: ✅ confirmed
```

---

### `/smartplug` — Manual plug control

| Subcommand | Effect |
| :--- | :--- |
| `/smartplug on` | Turn the plug on immediately |
| `/smartplug off` | Turn the plug off immediately |
| `/smartplug toggle` | Toggle based on current physical state |
| `/smartplug status` | Show MQTT connection state and power state |

**Example:**

```
/smartplug status
🔌 Smart Plug
• Device: Smart Plug 10A
• MQTT: 🟢 Connected
• Power: 🔌 ON

/smartplug off
🔴 Smart plug turned OFF ✅
Physical state confirmed.
```

---

## Auto-Resume on Bot Restart

When the bot starts, it checks `~/.pdagent/autobattery.json`. If auto-battery was previously enabled, it resumes monitoring automatically — no need to run `/autobattery on` again after a reboot or update.

---

## Hardware Compatibility

| Device | Status |
| :--- | :--- |
| **Qubo Smart Plug 10A** | ✅ Tested and confirmed |
| Other Qubo plugs using the same platform | 🔲 Likely compatible — set `QUBO_DEVICE_NAME` to match |
| Non-Qubo smart plugs | ❌ Not supported (Qubo's proprietary MQTT API is used) |

---

## Troubleshooting

**"QUBO_USERNAME and QUBO_PASSWORD must be set"**
- Add credentials to `~/.pdagent/config` as shown in Setup above.

**"Qubo device 'Smart Plug 10A' was not found"**
- Only raised when your account has 2+ devices and none match. Open the Qubo app, note the exact device name, and update `QUBO_DEVICE_NAME` in your config to match (case-insensitive). Accounts with a single device skip this check entirely.

**"Timed out connecting to Qubo MQTT (TCP 8883)"**
- Port 8883 may be blocked by your firewall or router. Ensure outbound TCP 8883 is allowed.
- Check your internet connection.

**Plug command sent but state unconfirmed**
- The MQTT monitor subscription didn't receive a state-change event within 8 s.
- The plug usually still executed the command — verify with `/smartplug status`.
- If it happens repeatedly, the plug's firmware may not send state confirmations; the bot will still retry at the next poll cycle.

**Auto battery not resuming after restart**
- Make sure `/autobattery on` was used at least once (this saves state to disk).
- Check `~/.pdagent/autobattery.json` — it should contain `"enabled": true` and a valid `user_id`.

"""Qubo smart plug MQTT client.

This module embeds the full async Qubo client (login, token refresh, device
sync, MQTT connect/subscribe, power control) directly into PD Agent.  No
separate local service is required — users only need to set QUBO_USERNAME,
QUBO_PASSWORD, and QUBO_DEVICE_NAME in their ~/.pdagent/config.

Dependency note:  paho-mqtt (paho-mqtt>=2.1,<3) and truststore (>=0.9.1) must
be installed.  Both are imported lazily inside each method so the cost is only
paid when the battery manager actually starts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Qubo cloud constants (copied from qubo-controller-v2-final/app.py) ──────
BASE_URL = "https://srvcapp.platform.quboworld.com/"
APP_ID = "934488E68332E88B1E0F9AF552840184955629777525A195949C0BE97DEF6455"
LOGIN_DEVICE_NAME = "LAN-Qubo-Controller"
DEVICE_ATTRIBUTE = "HomeAssistant|Server|Integration"
MQTT_HOST = "mqtt.platform.quboworld.com"
MQTT_PORT = 8883
PRODUCT_ID = "d10e4bfb0153496e8e8bb955f7ebe413"

# ── Reconnect tunables ────────────────────────────────────────────────────────
MQTT_RECONNECT_MIN_SECONDS = 2.0
MQTT_RECONNECT_MAX_SECONDS = 60.0
COMMAND_CONFIRM_TIMEOUT = 8.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick(obj: Any, *keys: str) -> Any:
    """Return the first non-None value from dict *obj* matching any of *keys*."""
    if not isinstance(obj, dict):
        return None
    for key in keys:
        value = obj.get(key)
        if value is not None:
            return value
    return None


def _unwrap(data: Any) -> dict:
    """Unwrap common Qubo response envelope wrappers."""
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected Qubo response type: {type(data).__name__}")
    for key in ("data", "result", "response"):
        wrapped = data.get(key)
        if isinstance(wrapped, dict) and not any(
            k in data for k in ("accessToken", "refreshToken", "uuid", "devices")
        ):
            return wrapped
    return data


@dataclass(frozen=True)
class DeviceInfo:
    device_uuid: str
    unit_uuid: str
    device_name: str
    handle_name: str


class QuboClient:
    """Async Qubo smart plug client.

    Lifecycle::

        client = QuboClient("user@example.com", "password", "Smart Plug 10A")
        await client.start()          # login + device sync + MQTT connect
        await client.set_power(True)  # turn ON
        await client.set_power(False) # turn OFF
        info = await client.get_status()
        await client.stop()           # disconnect cleanly

    The client maintains an internal maintenance loop that reconnects MQTT
    and refreshes tokens automatically.
    """

    def __init__(
        self,
        username: str,
        password: str,
        device_name: str = "Smart Plug 10A",
    ) -> None:
        self.username = username
        self.password = password
        self.device_name = device_name
        self.client_id: str = uuid.uuid4().hex[:16]

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_uuid: Optional[str] = None
        self.expires_at: float = 0.0

        self.device: Optional[DeviceInfo] = None
        self.state: Optional[bool] = None  # True=ON, False=OFF, None=unknown
        self.available: bool = False

        # asyncio primitives — created when start() is called so they are
        # always bound to the running event loop.
        self._mqtt_ready: Optional[asyncio.Event] = None
        self._state_event: Optional[asyncio.Event] = None
        self._token_lock: Optional[asyncio.Lock] = None
        self._mqtt_lock: Optional[asyncio.Lock] = None
        # Stored so MQTT thread callbacks can schedule event-loop wakeups safely.
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._mqtt: Any = None  # paho.mqtt.client.Client | None
        self._stopping: bool = False
        self._maintenance_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def topic(self, direction: str) -> str:
        """Build the MQTT topic for this device (direction: 'monitor' or 'control')."""
        if not self.device:
            raise RuntimeError("Client not yet authenticated/synced")
        return (
            f"/{direction}/{self.device.unit_uuid}/"
            f"{self.device.device_uuid}/lcSwitchControl"
        )

    async def start(self) -> None:
        """Login to Qubo cloud, discover device, connect MQTT."""
        # Capture the running loop so MQTT thread callbacks can schedule
        # event-loop wakeups via call_soon_threadsafe (thread-safe).
        self._loop = asyncio.get_running_loop()
        self._mqtt_ready = asyncio.Event()
        self._state_event = asyncio.Event()
        self._token_lock = asyncio.Lock()
        self._mqtt_lock = asyncio.Lock()

        self._stopping = False
        await self.login()
        await self.sync_devices()
        await self.connect_mqtt()
        self._maintenance_task = asyncio.create_task(
            self._maintenance_loop(), name="qubo-maintenance"
        )
        logger.info("QuboClient started (device: %s)", self.device_name)

    async def stop(self) -> None:
        """Disconnect MQTT and cancel the maintenance loop."""
        self._stopping = True
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
            self._maintenance_task = None
        await self._disconnect_mqtt()
        logger.info("QuboClient stopped")

    # ── Authentication ────────────────────────────────────────────────────────

    async def login(self) -> None:
        """Authenticate with Qubo cloud and store tokens."""
        import aiohttp  # lazy import

        url = f"{BASE_URL}sms/api/v4/sp/{PRODUCT_ID}/user/login"
        payload = {
            "accessToken": "",
            "deviceAttribute": DEVICE_ATTRIBUTE,
            "username": self.username,
            "password": self.password,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "App-Id": APP_ID,
            "Login-Device-Name": LOGIN_DEVICE_NAME,
            "Source": "ANDROID",
            "Source-Device-Id": self.client_id,
            "Token-Type": "USER",
        }

        try:
            import truststore
            ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        except ImportError:
            connector = aiohttp.TCPConnector(ssl=True)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                params={"system": "CS"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(
                        f"Qubo login failed ({response.status}): {body[:500]}"
                    )
                try:
                    data = _unwrap(json.loads(body))
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Qubo login returned non-JSON: {body[:500]}"
                    ) from exc

        access_token = _pick(data, "accessToken", "access_token")
        refresh_token = _pick(data, "refreshToken", "refresh_token")
        user_uuid = _pick(data, "uuid", "userUUID", "userUuid")

        if not access_token or not user_uuid:
            raise RuntimeError(
                "Qubo login succeeded but accessToken/user UUID was not found. "
                f"Response keys: {list(data.keys())}"
            )

        expires_in = float(_pick(data, "expires_in", "expiresIn") or 3600)
        self.access_token = str(access_token)
        self.refresh_token = str(refresh_token) if refresh_token else None
        self.user_uuid = str(user_uuid)
        # Refresh one minute before nominal expiry.
        self.expires_at = time.time() + max(60.0, expires_in) - 60.0
        logger.info("Qubo authentication succeeded (user_uuid=%s)", self.user_uuid)

    async def refresh_token_if_needed(self, force: bool = False) -> None:
        """Refresh access token when it is close to expiry."""
        if not force and time.time() < self.expires_at:
            return

        assert self._token_lock is not None  # set in start()
        async with self._token_lock:
            if not force and time.time() < self.expires_at:
                return

            if not self.user_uuid or not self.access_token or not self.refresh_token:
                await self.login()
                return

            import aiohttp  # lazy import

            url = (
                f"{BASE_URL}sms/api/v1/sp/{PRODUCT_ID}/users/"
                f"{self.user_uuid}/auth/refresh"
            )
            payload = {
                "accessToken": self.access_token,
                "refreshToken": self.refresh_token,
            }
            headers = {
                "Accept": "*/*",
                "Login-Device-Name": LOGIN_DEVICE_NAME,
                "Source-Device-Id": self.client_id,
                "Token-Type": "USER",
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as response:
                        body = await response.text()
                        if response.status >= 400:
                            raise RuntimeError(
                                f"Qubo token refresh failed "
                                f"({response.status}): {body[:500]}"
                            )
                        data = _unwrap(json.loads(body))

                token = _pick(data, "accessToken", "access_token")
                new_refresh = _pick(data, "refreshToken", "refresh_token")
                if not token:
                    raise RuntimeError(
                        "Qubo refresh response did not contain accessToken"
                    )
                self.access_token = str(token)
                if new_refresh:
                    self.refresh_token = str(new_refresh)
                expires_in = float(_pick(data, "expires_in", "expiresIn") or 3600)
                self.expires_at = time.time() + max(60.0, expires_in) - 60.0
                logger.info("Qubo token refreshed")
                # MQTT authenticates with the access token — reconnect.
                await self.connect_mqtt(force=True)

            except Exception:
                logger.warning(
                    "Qubo token refresh failed; performing a full login",
                    exc_info=True,
                )
                await self.login()
                await self.connect_mqtt(force=True)

    # ── Device discovery ──────────────────────────────────────────────────────

    async def sync_devices(self) -> None:
        """Discover the target device from the Qubo cloud device list."""
        await self.refresh_token_if_needed()
        if not self.access_token or not self.user_uuid:
            raise RuntimeError("Not authenticated")

        import aiohttp  # lazy import

        url = (
            f"{BASE_URL}unit-entity-management/api/v6/sp/"
            f"{PRODUCT_ID}/units/sync"
        )
        headers = {
            "Accept": "*/*",
            "Login-Device-Name": LOGIN_DEVICE_NAME,
            "Source-Device-Id": self.client_id,
            "Subscriber-Key": self.access_token,
            "Token-Type": "USER",
            "User-UUID": self.user_uuid,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json={"syncType": 1},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(
                        f"Qubo device sync failed ({response.status}): {body[:500]}"
                    )
                data = _unwrap(json.loads(body))

        devices = data.get("devices", [])
        if not isinstance(devices, list):
            raise RuntimeError("Qubo sync returned an invalid devices list")

        wanted = self.device_name.strip().casefold()
        target = None
        if wanted:
            for device in devices:
                name = str(_pick(device, "deviceName", "name") or "")
                if name.strip().casefold() == wanted:
                    target = device
                    break

        if target is None and len(devices) == 1:
            # Only one device on this Qubo account — use it even if the
            # configured/default device name doesn't match. This lets the
            # device be discovered straight from the account credentials
            # instead of requiring an exact QUBO_DEVICE_NAME match.
            target = devices[0]
            logger.info(
                "QUBO_DEVICE_NAME '%s' did not match; using the only device "
                "found on this account instead",
                self.device_name,
            )

        if target is None:
            names = [
                str(_pick(d, "deviceName", "name") or "?") for d in devices
            ]
            raise RuntimeError(
                f"Qubo device '{self.device_name}' was not found. "
                f"Available devices: {names}"
            )

        device_uuid = _pick(target, "deviceUUID", "deviceUuid")
        unit_uuid = _pick(target, "unitUUID", "unitUuid")
        device_name = _pick(target, "deviceName", "name")
        handle_name = _pick(target, "handleName", "handle_name") or ""

        if not device_uuid or not unit_uuid:
            raise RuntimeError(
                "Qubo device found but deviceUUID/unitUUID is missing"
            )

        self.device = DeviceInfo(
            device_uuid=str(device_uuid),
            unit_uuid=str(unit_uuid),
            device_name=str(device_name or self.device_name),
            handle_name=str(handle_name),
        )
        logger.info(
            "Qubo device discovered: %s (uuid=%s)",
            self.device.device_name,
            self.device.device_uuid,
        )

    # ── MQTT ──────────────────────────────────────────────────────────────────

    def _on_connect(
        self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any
    ) -> None:
        """Called by paho-mqtt network thread when MQTT connection is established.

        Uses call_soon_threadsafe to safely signal the asyncio event loop.
        """
        if reason_code == 0:
            self.available = True
            try:
                client.subscribe(self.topic("monitor"), qos=0)
                logger.info("Qubo MQTT connected and subscribed to monitor topic")
            except Exception:
                logger.warning(
                    "Qubo MQTT: failed to subscribe after connect", exc_info=True
                )
            if self._loop and self._mqtt_ready:
                self._loop.call_soon_threadsafe(self._mqtt_ready.set)
        else:
            logger.warning("Qubo MQTT connect failed: reason_code=%s", reason_code)

    def _on_disconnect(
        self, client: Any, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any
    ) -> None:
        """Called by paho-mqtt network thread when MQTT connection is lost.

        Uses call_soon_threadsafe to safely signal the asyncio event loop.
        """
        self.available = False
        if self._loop and self._mqtt_ready:
            self._loop.call_soon_threadsafe(self._mqtt_ready.clear)
        logger.warning("Qubo MQTT disconnected (reason_code=%s)", reason_code)

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        """Parse incoming Qubo state-change MQTT messages.

        Called from paho network thread.  Signals the asyncio event loop via
        call_soon_threadsafe so set_power()'s wait_for can wake up safely.
        """
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            state_data = (
                payload.get("devices", {})
                .get("services", {})
                .get("lcSwitchControl", {})
                .get("events", {})
                .get("stateChanged", {})
            )
            power = state_data.get("power")
            if power not in ("on", "off"):
                return
            self.state = power == "on"
            if self._loop and self._state_event:
                self._loop.call_soon_threadsafe(self._state_event.set)
        except Exception:
            logger.debug(
                "Ignoring unparseable Qubo MQTT state message", exc_info=True
            )

    async def connect_mqtt(self, force: bool = False) -> None:
        """Establish the MQTT connection (or reconnect if already exists)."""
        if not self.user_uuid or not self.access_token or not self.device:
            raise RuntimeError("Authentication/device discovery is incomplete")
        if self._mqtt_lock is None or self._mqtt_ready is None:
            raise RuntimeError("QuboClient.start() has not been called")

        import paho.mqtt.client as mqtt  # lazy import

        async with self._mqtt_lock:
            if not force and self._mqtt_ready.is_set() and self._mqtt is not None:
                return

            old = self._mqtt
            self._mqtt = None
            self._mqtt_ready.clear()
            self.available = False

            if old:
                try:
                    old.loop_stop()
                    old.disconnect()
                except Exception:
                    pass

            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"pdagent-qubo-{self.client_id}",
                protocol=mqtt.MQTTv311,
            )
            client.username_pw_set(self.user_uuid, self.access_token)
            client.tls_set_context(ssl.create_default_context())
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            self._mqtt = client

            def _connect() -> None:
                client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
                client.loop_start()

            await asyncio.to_thread(_connect)

            try:
                await asyncio.wait_for(self._mqtt_ready.wait(), timeout=15)
            except asyncio.TimeoutError as exc:
                try:
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    pass
                self._mqtt = None
                raise RuntimeError(
                    "Timed out connecting to Qubo MQTT (TCP 8883)"
                ) from exc

    async def _disconnect_mqtt(self) -> None:
        """Gracefully stop and disconnect the MQTT client."""
        if self._mqtt_lock is None:
            return
        async with self._mqtt_lock:
            old = self._mqtt
            self._mqtt = None
            if self._mqtt_ready:
                self._mqtt_ready.clear()
            self.available = False
            if old:
                try:
                    old.loop_stop()
                    old.disconnect()
                except Exception:
                    pass

    async def _maintenance_loop(self) -> None:
        """Background loop that keeps tokens fresh and MQTT connected."""
        backoff = MQTT_RECONNECT_MIN_SECONDS
        while not self._stopping:
            try:
                await self.refresh_token_if_needed()
                if self._mqtt_ready and not self._mqtt_ready.is_set():
                    await self.connect_mqtt()
                backoff = MQTT_RECONNECT_MIN_SECONDS
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning(
                    "Qubo maintenance/reconnect attempt failed; retrying in %.0fs",
                    backoff,
                    exc_info=True,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MQTT_RECONNECT_MAX_SECONDS)

    # ── Control ───────────────────────────────────────────────────────────────

    async def set_power(self, on: bool) -> dict:
        """Turn the smart plug on (on=True) or off (on=False).

        Waits up to COMMAND_CONFIRM_TIMEOUT seconds for the physical state
        confirmation from the Qubo MQTT monitor topic.

        Returns a dict with keys: command, confirmed, state.
        """
        if self._mqtt_ready is None or self._state_event is None:
            raise RuntimeError("QuboClient.start() has not been called")

        await self.refresh_token_if_needed()
        if not self._mqtt_ready.is_set():
            await self.connect_mqtt()
        if not self._mqtt:
            raise RuntimeError("Qubo MQTT is not connected")

        power = "on" if on else "off"
        timestamp = int(time.time() * 1000)
        payload = {
            "command": {
                "devices": {
                    "deviceUUID": self.device.device_uuid,
                    "handleName": self.device.handle_name,
                    "services": {
                        "lcSwitchControl": {
                            "attributes": {"power": power},
                            "instanceId": 0,
                        }
                    },
                }
            },
            "deviceUUID": self.device.device_uuid,
            "msgSequenceId": timestamp,
            "srcDeviceId": self.client_id,
            "timestamp": timestamp,
        }

        import paho.mqtt.client as mqtt  # lazy import for rc constant

        self._state_event.clear()
        result = self._mqtt.publish(
            self.topic("control"),
            json.dumps(payload),
            qos=0,
        )
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Qubo MQTT publish failed: rc={result.rc}")

        try:
            await asyncio.wait_for(
                self._state_event.wait(),
                timeout=COMMAND_CONFIRM_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return {
                "command": power,
                "confirmed": False,
                "state": self.state,
            }

        return {
            "command": power,
            "confirmed": self.state == on,
            "state": self.state,
        }

    async def get_status(self) -> dict:
        """Return current plug connection/state information."""
        return {
            "connected": bool(self._mqtt_ready and self._mqtt_ready.is_set()),
            "available": self.available,
            "state": (
                "ON" if self.state is True
                else "OFF" if self.state is False
                else "UNKNOWN"
            ),
            "device": self.device.device_name if self.device else None,
            "device_uuid": self.device.device_uuid if self.device else None,
        }

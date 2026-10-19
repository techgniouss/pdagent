import json
from pocket_desk_agent.config import Config
from pocket_desk_agent.handlers import smart_plug
from pocket_desk_agent.command_map import COMMAND_REGISTRY


def test_smart_plug_seeds_from_config_and_overrides(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "autobattery.json"
    monkeypatch.setattr(smart_plug, "_STATE_FILE", state_file)

    # When no state file exists, thresholds come from Config defaults or values
    monkeypatch.setattr(Config, "BATTERY_HIGH_THRESHOLD", 88)
    monkeypatch.setattr(Config, "BATTERY_LOW_THRESHOLD", 22)
    monkeypatch.setattr(Config, "BATTERY_POLL_INTERVAL", 120)

    smart_plug._load_state()
    assert smart_plug._high_threshold == 88
    assert smart_plug._low_threshold == 22
    assert smart_plug._poll_interval == 120

    # When state file exists, it overrides Config
    state_file.write_text(
        json.dumps({
            "enabled": True,
            "high_threshold": 92,
            "low_threshold": 18,
            "poll_interval": 60,
            "user_id": 999,
        }),
        encoding="utf-8",
    )
    smart_plug._load_state()
    assert smart_plug._enabled is True
    assert smart_plug._high_threshold == 92
    assert smart_plug._low_threshold == 18
    assert smart_plug._poll_interval == 60
    assert smart_plug._user_id == 999


def test_smart_plug_command_registration() -> None:
    # Ensure handlers are present in COMMAND_REGISTRY
    reg_dict = {name: handler for name, handler, _ in COMMAND_REGISTRY}
    assert "autobattery" in reg_dict
    assert "smartplug" in reg_dict
    assert reg_dict["autobattery"] is smart_plug.autobattery_command
    assert reg_dict["smartplug"] is smart_plug.smartplug_command


def test_autobattery_off_ensures_plug_on(monkeypatch) -> None:
    import asyncio

    power_calls = []
    stopped = {"monitor": False, "plug": False}
    replies = []

    class DummyPlug:
        async def set_power(self, on: bool):
            power_calls.append(on)
            return {"command": "on" if on else "off", "confirmed": True, "state": True}

    async def dummy_get_or_create_plug():
        return DummyPlug()

    async def dummy_stop_monitor():
        stopped["monitor"] = True

    async def dummy_stop_plug():
        stopped["plug"] = True

    class DummyMessage:
        async def reply_text(self, text: str):
            replies.append(text)

    class DummyUser:
        id = 12345

    class DummyUpdate:
        message = DummyMessage()
        effective_user = DummyUser()

    class DummyContext:
        args = ["off"]

    monkeypatch.setattr(smart_plug, "_get_or_create_plug", dummy_get_or_create_plug)
    monkeypatch.setattr(smart_plug, "_stop_monitor", dummy_stop_monitor)
    monkeypatch.setattr(smart_plug, "_stop_plug", dummy_stop_plug)
    monkeypatch.setattr(smart_plug, "_save_state", lambda: None)

    smart_plug._enabled = True

    async def _run():
        await smart_plug.autobattery_command(DummyUpdate(), DummyContext())

    asyncio.run(_run())

    assert smart_plug._enabled is False
    assert power_calls == [True]
    assert stopped["monitor"] is True
    assert stopped["plug"] is True
    assert len(replies) == 1
    assert "turned ON" in replies[0]


def test_qubo_client_connect_mqtt_force(monkeypatch) -> None:
    from pocket_desk_agent.qubo_client import QuboClient, DeviceInfo
    import asyncio

    async def _run():
        client = QuboClient("user@example.com", "secret", "Smart Plug 10A")
        client.user_uuid = "uuid-123"
        client.access_token = "token-abc"
        client.device = DeviceInfo(
            device_uuid="dev-1",
            unit_uuid="unit-1",
            device_name="Smart Plug 10A",
            handle_name="h1",
        )
        client._mqtt_ready = asyncio.Event()
        client._mqtt_lock = asyncio.Lock()
        client._mqtt = object()
        client._mqtt_ready.set()

        # Without force, early return when ready and mqtt is not None
        await client.connect_mqtt(force=False)
        assert client._mqtt is not None
        assert client._mqtt_ready.is_set()

    asyncio.run(_run())




def test_battery_manager_retries_until_plug_is_reachable(monkeypatch) -> None:
    import asyncio

    from pocket_desk_agent.handlers import smart_plug

    attempts = {"n": 0}
    sleeps: list[float] = []

    class FakePlug:
        async def get_status(self):
            raise asyncio.CancelledError  # stop right after the plug connected

    async def flaky_connect():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("network not up yet")
        return FakePlug()

    async def fake_sleep(delay):
        sleeps.append(delay)

    class Bot:
        def __init__(self):
            self.sent: list[str] = []

        async def send_message(self, chat_id, text):
            self.sent.append(text)

    bot = Bot()
    monkeypatch.setattr(smart_plug, "_get_or_create_plug", flaky_connect)
    monkeypatch.setattr(smart_plug.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(smart_plug, "_bot", bot)
    monkeypatch.setattr(smart_plug, "_user_id", 5)

    try:
        asyncio.run(smart_plug._battery_manager_loop())
    except asyncio.CancelledError:
        pass

    assert attempts["n"] == 3
    assert sleeps == [30, 60]  # exponential backoff between the two failures
    assert len(bot.sent) == 1 and "keep retrying" in bot.sent[0]


def test_battery_manager_gives_up_when_credentials_missing(monkeypatch) -> None:
    import asyncio

    from pocket_desk_agent.handlers import smart_plug

    async def no_creds():
        raise smart_plug.PlugNotConfiguredError("Qubo credentials are not set.")

    class Bot:
        def __init__(self):
            self.sent: list[str] = []

        async def send_message(self, chat_id, text):
            self.sent.append(text)

    bot = Bot()
    monkeypatch.setattr(smart_plug, "_get_or_create_plug", no_creds)
    monkeypatch.setattr(smart_plug, "_bot", bot)
    monkeypatch.setattr(smart_plug, "_user_id", 5)

    asyncio.run(smart_plug._battery_manager_loop())  # returns instead of looping forever

    assert len(bot.sent) == 1 and "can't start" in bot.sent[0]

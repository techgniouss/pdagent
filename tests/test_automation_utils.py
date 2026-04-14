from pocket_desk_agent.automation_utils import press_key, send_hotkey, write_text


class _FakePyAutoGUI:
    class FailSafeException(Exception):
        pass

    def __init__(self):
        self.FAILSAFE = True
        self.calls = []
        self._write_failed_once = False

    def write(self, text, interval=0.0):
        self.calls.append(("write", text, interval, self.FAILSAFE))
        if self.FAILSAFE and not self._write_failed_once:
            self._write_failed_once = True
            raise self.FailSafeException("mouse in corner")

    def press(self, key):
        self.calls.append(("press", key, self.FAILSAFE))

    def hotkey(self, *keys):
        self.calls.append(("hotkey", keys, self.FAILSAFE))


def test_write_text_retries_with_failsafe_disabled_for_keyboard_only_actions():
    pyautogui = _FakePyAutoGUI()

    used_fallback = write_text(pyautogui, "1234", interval=0.05)

    assert used_fallback is True
    assert pyautogui.FAILSAFE is True
    assert pyautogui.calls == [
        ("write", "1234", 0.05, True),
        ("write", "1234", 0.05, False),
    ]


def test_press_key_and_send_hotkey_keep_failsafe_enabled_when_no_retry_is_needed():
    pyautogui = _FakePyAutoGUI()

    assert press_key(pyautogui, "enter") is False
    assert send_hotkey(pyautogui, "ctrl", "v") is False
    assert pyautogui.FAILSAFE is True
    assert pyautogui.calls == [
        ("press", "enter", True),
        ("hotkey", ("ctrl", "v"), True),
    ]

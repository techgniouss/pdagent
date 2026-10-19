"""Tests for message splitting and background task helpers."""
import asyncio

from pocket_desk_agent.async_utils import reply_long_text, spawn_background_task, split_message


def test_short_text_is_one_chunk() -> None:
    assert split_message("hello") == ["hello"]


def test_long_text_splits_within_limit_and_keeps_content() -> None:
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(300))
    chunks = split_message(text, limit=500)
    assert len(chunks) > 1
    assert all(0 < len(c) <= 500 for c in chunks)
    assert "".join(c.replace("\n", "") for c in chunks).replace(" ", "") == text.replace("\n", "").replace(" ", "")


def test_unbroken_token_is_hard_split() -> None:
    chunks = split_message("a" * 1000, limit=300)
    assert [len(c) for c in chunks] == [300, 300, 300, 100]


def test_reply_long_text_sends_every_chunk() -> None:
    sent: list[str] = []

    class Msg:
        async def reply_text(self, text, **kwargs):
            sent.append(text)

    asyncio.run(reply_long_text(Msg(), "word " * 2000))
    assert len(sent) > 1 and all(len(c) <= 4096 for c in sent)


def test_spawn_background_task_runs_to_completion() -> None:
    async def run() -> int:
        result: list[int] = []

        async def work() -> None:
            await asyncio.sleep(0)
            result.append(1)

        task = spawn_background_task(work())
        await task
        return len(result)

    assert asyncio.run(run()) == 1

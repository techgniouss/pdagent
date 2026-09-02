from pocket_desk_agent.handlers import _shared
from pocket_desk_agent.ai_router import AIRouter


def test_shared_ai_router_is_wired_to_shared_clients() -> None:
    assert isinstance(_shared.ai_router, AIRouter)
    assert _shared.ai_router.gemini is _shared.gemini_client
    assert _shared.ai_router.nvidia is _shared.nvidia_client

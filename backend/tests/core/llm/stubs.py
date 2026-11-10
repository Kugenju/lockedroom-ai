"""Shared stubs for LLM backend tests (no network involved)."""

from types import SimpleNamespace


def make_completion(content: str, prompt_tokens: int = 10, completion_tokens: int = 5):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        model="stub-model",
    )


def make_stream_chunk(text: str | None):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class StubCompletions:
    def __init__(self):
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            async def gen():
                for piece in ["你", "好", None, "，玩家"]:
                    yield make_stream_chunk(piece)
            return gen()
        return make_completion("你好，玩家")

    def init_args(self):
        return self.calls[-1] if self.calls else {}


class StubClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=StubCompletions())

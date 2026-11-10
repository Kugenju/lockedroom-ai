"""Build a chat model from settings."""

from app.core.config import Settings
from app.core.llm.base import BaseChatModel
from app.core.llm.openai_compat import OpenAICompatChat


def create_chat_model(settings: Settings | None = None, model: str | None = None) -> BaseChatModel:
    s = settings or Settings()
    model = model or s.model
    if s.inference_service == "fake":
        from app.core.llm.fake import FakeLLM

        return FakeLLM("（这是本地假模型回复，用于无 API 环境的开发调试。）")
    if s.inference_service == "ollama":
        base_url = s.ollama_url.rstrip("/") + "/v1"
        api_key = "ollama"  # Ollama ignores the key but the SDK requires one
    else:
        base_url = s.openai_api_base
        api_key = s.api_key
    # DeepSeek thinking mode (enabled server-side by default) — dialogue wants it off
    # for latency; see https://api-docs.deepseek.com/guides/thinking_mode
    extra_body = None
    if s.inference_service == "deepseek":
        extra_body = {"thinking": {"type": "enabled" if s.thinking_enabled else "disabled"}}
    return OpenAICompatChat(
        model=model,
        api_key=api_key,
        base_url=base_url,
        default_temperature=s.temperature,
        default_max_tokens=s.max_tokens,
        extra_body=extra_body,
    )

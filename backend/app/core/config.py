"""Application settings, overridable via SM_* environment variables or a .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    inference_service: str = "deepseek"  # deepseek | openai | ollama | any openai-compatible
    model: str = "deepseek-flash"
    api_key: str = ""
    openai_api_base: str | None = None
    ollama_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 2048
    scripts_dir: str = "backend/app/scripts"
    judge_enabled: bool = True  # LLM adjudication of rule-based leak findings
    judge_model: str | None = None  # None = reuse the main chat model
    thinking_enabled: bool = False  # DeepSeek thinking mode (dialogue default off)
    database_url: str | None = None  # None = sqlite at ./data/scriptmurder.db

    model_config = SettingsConfigDict(env_prefix="SM_", env_file=".env", extra="ignore")

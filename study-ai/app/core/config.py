import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Study AI MVP"
    local_llm_url: str = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:11434/api/generate")
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:3b")
    use_mock_llm: bool = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]


settings = Settings()

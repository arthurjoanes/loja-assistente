from datetime import date
from typing import Self
from urllib.parse import urlsplit

from openai.types.shared import ReasoningEffort
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://loja:loja_local@db:5432/loja_assistente"
    reference_date: date = date(2026, 8, 17)
    dataset_version: str = "synthetic-v1"
    allowed_origins: list[str] = ["http://localhost:3102", "http://127.0.0.1:3102"]
    session_secret: str = "loja-assistente-local-demo-change-for-https"
    session_hours: int = Field(default=8, ge=1, le=24)
    cookie_secure: bool = False
    demo_mode: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini-2025-04-14"
    openai_base_url: str = "https://api.openai.com/v1/"
    openai_reasoning_effort: ReasoningEffort | None = None
    llm_enabled: bool = False

    @field_validator("openai_reasoning_effort", mode="before")
    @classmethod
    def empty_reasoning_uses_provider_default(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_inference_endpoint(self) -> Self:
        endpoint = urlsplit(self.openai_base_url)
        host = endpoint.hostname or ""
        is_openai = host == "api.openai.com" and endpoint.path.rstrip("/") == "/v1"
        is_azure = host.endswith((".openai.azure.com", ".services.ai.azure.com")) and (
            endpoint.path.rstrip("/") == "/openai/v1"
        )
        if (
            endpoint.scheme != "https"
            or endpoint.username
            or endpoint.password
            or endpoint.query
            or endpoint.fragment
            or endpoint.port not in (None, 443)
            or not (is_openai or is_azure)
        ):
            raise ValueError(
                "Use o endpoint HTTPS de inferência OpenAI v1 ou Azure /openai/v1/, sem projeto, query ou credenciais na URL."
            )
        self.openai_base_url = self.openai_base_url.rstrip("/") + "/"
        return self

    @model_validator(mode="after")
    def reject_default_secret_outside_demo(self) -> Self:
        if not self.demo_mode and (
            self.session_secret == "loja-assistente-local-demo-change-for-https"
            or len(self.session_secret) < 32
        ):
            raise ValueError("Fora de DEMO_MODE, SESSION_SECRET deve ter pelo menos 32 caracteres.")
        return self


settings = Settings()

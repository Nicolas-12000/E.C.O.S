from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    env: str = "dev"
    debug: bool = True
    # En Render: false = router RAG (512MB). true = API completa (what-if, pronóstico, movilidad…).
    enable_full_api: bool = Field(default=False, validation_alias="ECOS_FULL_API")
    grpc_port: int = Field(default=0, validation_alias="GRPC_PORT")  # Render: 0 (solo $PORT)

    # Groq (LLM para RAG)
    groq_api_key: str = ""
    # Calidad episodemiología + español; reemplazo recomendado por Groq frente a Llama 3.3 70B.
    groq_model: str = "openai/gpt-oss-120b"

    # Supabase (opcional)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Database (opcional — el backend funciona sin DB, con Parquet/CSV)
    database_url: str = ""
    supabase_db_url: str = ""

    # OpenWeather (opcional — solo si quieres datos de clima actual)
    openweather_api_key: str = ""

    # Render/Vercel: lista separada por comas (no JSON).
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")

    _DEFAULT_CORS_ORIGINS = (
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    )

    @property
    def resolved_cors_origins(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return list(self._DEFAULT_CORS_ORIGINS)

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def lite_production(self) -> bool:
        return self.env == "production" and not self.enable_full_api

    def resolved_database_url(self) -> str | None:
        """Return the first available database URL, or None."""
        for url in [self.database_url, self.supabase_db_url]:
            if url:
                return url
        return None


settings = Settings()

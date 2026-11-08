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

    chat_demo_auth_required: bool = Field(default=True, validation_alias="CHAT_DEMO_AUTH_REQUIRED")
    chat_demo_token_secret: str = Field(default="", validation_alias="CHAT_DEMO_TOKEN_SECRET")

    # Render/Vercel: lista separada por comas (no JSON).
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")
    # Previews de Vercel (URL distinta a producción) — ver resolved_cors_origin_regex.
    cors_allow_vercel: bool = Field(default=True, validation_alias="CORS_ALLOW_VERCEL")
    cors_origin_regex: str = Field(default="", validation_alias="CORS_ORIGIN_REGEX")

    _DEFAULT_CORS_ORIGINS = (
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    )

    @property
    def resolved_cors_origins(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        origins = (
            [origin.strip() for origin in raw.split(",") if origin.strip()]
            if raw
            else list(self._DEFAULT_CORS_ORIGINS)
        )
        return origins

    @property
    def resolved_cors_origin_regex(self) -> str | None:
        custom = (self.cors_origin_regex or "").strip()
        if custom:
            return custom
        if self.cors_allow_vercel or self.env == "production":
            # Producción y previews: https://tu-app.vercel.app, https://e-c-o-xxx-teams.vercel.app, etc.
            return r"https://.*\.vercel\.app"
        return None

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

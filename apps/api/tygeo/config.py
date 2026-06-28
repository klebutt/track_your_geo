from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tygeo_model: str = "gpt-4o-mini"
    tygeo_probe_model: str = "gpt-4o-mini-search-preview"
    tygeo_enabled_probes: str = "gpt-4o-mini-search-preview"
    tygeo_search_context_size: str = "low"
    tygeo_database_url: str = "sqlite:///./data/tygeo.db"
    tygeo_pilot_dir: str = "pilot"
    tygeo_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openai_api_key: str | None = None
    perplexity_api_key: str | None = None
    gemini_api_key: str | None = None

    @property
    def enabled_probe_models(self) -> list[str]:
        raw = self.tygeo_enabled_probes or self.tygeo_probe_model
        return [m.strip() for m in raw.split(",") if m.strip()]

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.tygeo_allowed_origins.split(",") if o.strip()]

    @property
    def pilot_dir_path(self) -> Path:
        return Path(self.tygeo_pilot_dir).resolve()

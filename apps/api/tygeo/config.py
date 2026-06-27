from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tygeo_model: str = "gpt-4o-mini"
    tygeo_probe_model: str = "gpt-4o-mini-search-preview"
    tygeo_search_context_size: str = "low"
    tygeo_database_url: str = "sqlite:///./data/tygeo.db"
    tygeo_pilot_dir: str = "pilot"
    openai_api_key: str | None = None

    @property
    def pilot_dir_path(self) -> Path:
        return Path(self.tygeo_pilot_dir).resolve()

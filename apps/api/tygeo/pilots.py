from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from tygeo.hardcoded_pilots import HARDCODED_PILOT_SPECS


class PilotProfile(BaseModel):
    id: str
    brand_name: str
    location: str
    competitors: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    seed_domains: list[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> PilotProfile:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid pilot file: {path}")
        return cls.model_validate(raw)

    def format_query(
        self,
        template: str,
        brand: str | None = None,
        location: str | None = None,
    ) -> str:
        b = brand or self.brand_name
        loc = location or self.location
        return template.format(brand=b, location=loc)


def list_pilots(pilot_dir: Path) -> list[PilotProfile]:
    """Return built-in pilots (real brands). YAML under ``pilot_dir`` is ignored for listing."""
    return [PilotProfile.model_validate(spec) for spec in HARDCODED_PILOT_SPECS]


def load_pilot(pilot_dir: Path, pilot_id: str) -> PilotProfile | None:
    for p in list_pilots(pilot_dir):
        if p.id == pilot_id:
            return p
    return None

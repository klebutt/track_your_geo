from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_YAML_SUFFIXES = {".yaml", ".yml"}


class PilotProfile(BaseModel):
    id: str
    brand_name: str
    location: str
    competitors: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    seed_domains: list[str] = Field(default_factory=list)
    brand_domains: list[str] = Field(default_factory=list)

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
    """Return pilots loaded recursively from YAML files under ``pilot_dir``."""
    if not pilot_dir.is_dir():
        logger.warning("Pilot directory does not exist: %s", pilot_dir)
        return []

    pilots: list[PilotProfile] = []
    seen_ids: set[str] = set()
    for path in sorted(pilot_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _YAML_SUFFIXES:
            continue
        try:
            pilot = PilotProfile.from_yaml(path)
        except Exception as exc:
            logger.warning("Skipping invalid pilot file %s: %s", path, exc)
            continue
        if pilot.id in seen_ids:
            logger.warning("Duplicate pilot id %r in %s; skipping", pilot.id, path)
            continue
        seen_ids.add(pilot.id)
        pilots.append(pilot)
    return pilots


def load_pilot(pilot_dir: Path, pilot_id: str) -> PilotProfile | None:
    for p in list_pilots(pilot_dir):
        if p.id == pilot_id:
            return p
    return None

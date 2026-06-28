"""End-to-end smoke: execute_run with real LLMs for a single-query pilot."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from tygeo.analysis import execute_run  # noqa: E402
from tygeo.config import Settings  # noqa: E402
from tygeo.db import Base  # noqa: E402
from tygeo.pilots import PilotProfile  # noqa: E402


def main() -> int:
    settings = Settings()
    models = settings.enabled_probe_models
    print(f"Models: {models}")

    pilot = PilotProfile(
        id="smoke",
        brand_name="Dishoom",
        location="London, UK",
        competitors=["Hawksmoor"],
        queries=["What are the best Indian restaurants in {location}? Name specific venues."],
        brand_domains=["dishoom.com"],
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    run = execute_run(db, settings, pilot, brand_override=None, location_override=None)
    print(f"run.model_name: {run.model_name}")
    print(f"query_results: {len(run.query_results)} (expected {len(models)})")
    print(f"total_cost_usd: {run.total_cost_usd:.4f}")
    print(f"visibility_rate: {run.visibility_rate:.2f}")

    for qr in run.query_results:
        domains = [c["domain"] for c in (qr.cited_domains or [])]
        print(
            f"  [{qr.model_name}] brand={qr.brand_mentioned} "
            f"cost=${qr.cost_usd:.5f} domains={len(domains)}"
        )

    db.close()
    ok = len(run.query_results) == len(models) and run.total_cost_usd > 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

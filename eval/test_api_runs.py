"""API tests for async run creation."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tygeo.config import Settings
from tygeo.db import Base, init_db
from tygeo.main import app
from tygeo.models import Run


def test_post_run_returns_running_before_probes_finish(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TYGEO_ENABLED_PROBES", "gpt-4o-mini-search-preview")
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")

    pilot_dir = tmp_path / "pilots"
    pilot_dir.mkdir()
    (pilot_dir / "demo.yaml").write_text(
        "id: demo\nbrand_name: Demo\nlocation: UK\nqueries:\n  - Best tools in {location}?\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TYGEO_PILOT_DIR", str(pilot_dir))

    def fake_finish(run_id, pilot_id, *, brand_override, location_override):
        settings = Settings()
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            from tygeo.analysis import execute_run
            from tygeo.pilots import load_pilot

            pilot = load_pilot(settings.pilot_dir_path, pilot_id)
            run = db.query(Run).filter(Run.id == run_id).first()
            assert pilot is not None
            assert run is not None
            with patch("tygeo.analysis.run_geo_query_provider") as mock_probe:
                mock_probe.return_value = ("answer", {"cost_usd": 0.0, "latency_ms": 1.0, "prompt_tokens": 1, "completion_tokens": 1}, [], [], None)
                execute_run(
                    db,
                    settings,
                    pilot,
                    brand_override=brand_override,
                    location_override=location_override,
                    run=run,
                )
        finally:
            db.close()

    with patch("tygeo.main.finish_run_probes", side_effect=fake_finish):
        client = TestClient(app)
        res = client.post("/api/runs", json={"pilot_id": "demo"})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "running"
        assert body["query_results"] == []

        # Background runs synchronously under TestClient
        final = client.get(f"/api/runs/{body['id']}")
        assert final.status_code == 200
        assert final.json()["status"] == "completed"
        assert len(final.json()["query_results"]) == 1


def test_list_runs_filters_by_pilot_id(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")

    pilot_dir = tmp_path / "pilots"
    pilot_dir.mkdir()
    (pilot_dir / "alpha.yaml").write_text(
        "id: alpha\nbrand_name: Alpha\nlocation: UK\nqueries:\n  - q1\n",
        encoding="utf-8",
    )
    (pilot_dir / "beta.yaml").write_text(
        "id: beta\nbrand_name: Beta\nlocation: UK\nqueries:\n  - q1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TYGEO_PILOT_DIR", str(pilot_dir))

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            Run(
                pilot_id="alpha",
                brand_name="Alpha",
                location="UK",
                model_name="test",
                status="completed",
                visibility_rate=0.5,
            )
        )
        db.add(
            Run(
                pilot_id="beta",
                brand_name="Beta",
                location="UK",
                model_name="test",
                status="completed",
                visibility_rate=0.8,
            )
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    res = client.get("/api/runs", params={"pilot_id": "alpha", "limit": 1})
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["pilot_id"] == "alpha"
    assert body[0]["visibility_rate"] == 0.5

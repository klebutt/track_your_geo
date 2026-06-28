from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from tygeo.analysis import create_pending_run, finish_run_probes
from tygeo.config import Settings
from tygeo.db import get_session, init_db
from tygeo.models import Run
from tygeo.pilots import list_pilots, load_pilot
from tygeo.schemas import PilotDetail, PilotSummary, RunCreate, RunListItem, RunOut


def get_settings() -> Settings:
    return Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    db_path = settings.tygeo_database_url
    if db_path.startswith("sqlite:///./") or db_path.startswith("sqlite://"):
        Path("data").mkdir(parents=True, exist_ok=True)
    init_db(settings.tygeo_database_url)
    yield


app = FastAPI(title="Track Your GEO API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_session():
    yield from get_session()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/pilots", response_model=list[PilotSummary])
def api_list_pilots(settings: Settings = Depends(get_settings)):
    pilots = list_pilots(settings.pilot_dir_path)
    return [
        PilotSummary(
            id=p.id,
            brand_name=p.brand_name,
            location=p.location,
            query_count=len(p.queries),
        )
        for p in pilots
    ]


@app.get("/api/pilots/{pilot_id}", response_model=PilotDetail)
def api_get_pilot(pilot_id: str, settings: Settings = Depends(get_settings)):
    p = load_pilot(settings.pilot_dir_path, pilot_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return PilotDetail(
        id=p.id,
        brand_name=p.brand_name,
        location=p.location,
        query_count=len(p.queries),
        competitors=p.competitors,
        queries=p.queries,
        seed_domains=p.seed_domains,
        brand_domains=p.brand_domains,
    )


@app.post("/api/runs", response_model=RunOut)
def api_create_run(
    body: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
    settings: Settings = Depends(get_settings),
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.",
        )
    pilot = load_pilot(settings.pilot_dir_path, body.pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    run = create_pending_run(
        db,
        settings,
        pilot,
        brand_override=body.brand_name,
        location_override=body.location,
    )
    background_tasks.add_task(
        finish_run_probes,
        run.id,
        body.pilot_id,
        brand_override=body.brand_name,
        location_override=body.location,
    )
    return _load_run(db, run.id)


@app.get("/api/runs", response_model=list[RunListItem])
def api_list_runs(limit: int = 20, db: Session = Depends(db_session)):
    rows = (
        db.query(Run)
        .order_by(Run.created_at.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return rows


@app.get("/api/runs/{run_id}", response_model=RunOut)
def api_get_run(run_id: int, db: Session = Depends(db_session)):
    row = _load_run(db, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


def _load_run(db: Session, run_id: int) -> Run | None:
    return (
        db.query(Run)
        .options(
            joinedload(Run.query_results),
            joinedload(Run.recommendations),
        )
        .filter(Run.id == run_id)
        .first()
    )


def run_server() -> None:
    import uvicorn

    uvicorn.run("tygeo.main:app", host="127.0.0.1", port=8000, reload=True)

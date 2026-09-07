from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()

_engine = None
_SessionLocal = None


def init_db(database_url: str) -> None:
    global _engine, _SessionLocal
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    _engine = create_engine(database_url, connect_args=connect_args)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)
    _migrate_sqlite(_engine)


def _migrate_sqlite(engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    migrations: list[str] = []

    if "query_results" in tables:
        cols = {c["name"] for c in insp.get_columns("query_results")}
        if "cited_domains" not in cols:
            migrations.append("ALTER TABLE query_results ADD COLUMN cited_domains JSON")
        if "model_name" not in cols:
            migrations.append(
                "ALTER TABLE query_results ADD COLUMN model_name VARCHAR(256) DEFAULT ''"
            )
        if "sentiment" not in cols:
            migrations.append(
                "ALTER TABLE query_results ADD COLUMN sentiment VARCHAR(32) DEFAULT 'neutral'"
            )
        if "mention_position" not in cols:
            migrations.append(
                "ALTER TABLE query_results ADD COLUMN mention_position VARCHAR(32) DEFAULT 'not_mentioned'"
            )
        if "relevance_score" not in cols:
            migrations.append(
                "ALTER TABLE query_results ADD COLUMN relevance_score FLOAT DEFAULT 0.0"
            )

    if "runs" in tables:
        run_cols = {c["name"] for c in insp.get_columns("runs")}
        if "source_url" not in run_cols:
            migrations.append("ALTER TABLE runs ADD COLUMN source_url VARCHAR(2048)")
        if "profile_snapshot" not in run_cols:
            migrations.append("ALTER TABLE runs ADD COLUMN profile_snapshot JSON")

    for stmt in migrations:
        with engine.begin() as conn:
            conn.execute(text(stmt))


def get_engine():
    if _engine is None:
        raise RuntimeError("Database not initialized")
    return _engine


def get_session() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def new_session() -> Session:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized")
    return _SessionLocal()

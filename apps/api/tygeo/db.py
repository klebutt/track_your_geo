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
    if "query_results" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("query_results")}
    migrations: list[str] = []
    if "cited_domains" not in cols:
        migrations.append("ALTER TABLE query_results ADD COLUMN cited_domains JSON")
    if "model_name" not in cols:
        migrations.append(
            "ALTER TABLE query_results ADD COLUMN model_name VARCHAR(256) DEFAULT ''"
        )
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

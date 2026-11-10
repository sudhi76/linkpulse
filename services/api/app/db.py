from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


# pool_pre_ping checks a pooled connection before using it, so a database
# restart doesn't leave the API holding dead connections.
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with SessionLocal() as session:
        yield session


# Arbitrary constant naming the lock that serialises schema creation.
SCHEMA_LOCK_ID = 726_001


def create_schema(bind: Engine) -> None:
    """Create missing tables. Safe when several pods start at once: on
    PostgreSQL, a transaction-scoped advisory lock makes them take turns, so
    only the first creates the tables and the rest find them already there."""
    with bind.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": SCHEMA_LOCK_ID})
        Base.metadata.create_all(conn)

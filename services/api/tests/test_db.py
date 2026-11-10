from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.db import create_schema


def test_create_schema_is_idempotent():
    # Every pod runs this on startup, so running it again must be a no-op.
    engine = create_engine("sqlite://", poolclass=StaticPool)
    create_schema(engine)
    create_schema(engine)
    assert "links" in inspect(engine).get_table_names()

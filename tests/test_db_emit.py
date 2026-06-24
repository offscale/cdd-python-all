"""Test for DB generation."""

from openapi_client.db.emit import emit_db
from openapi_client.models import OpenAPI


def test_emit_db():
    """Test emit_db with spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    code = emit_db(spec)

    assert "class DBConfig:" in code
    assert (
        "def __init__(self, database_url: Optional[str] = None, ephemeral: bool = False):"
        in code
    )
    assert "def get_engine(config: DBConfig) -> Engine:" in code
    assert "def init_db(engine: Engine) -> None:" in code
    assert "def setup_database(" in code
    assert "def get_db_session() -> Generator[Session, None, None]:" in code
    assert "self.database_url = 'sqlite:///:memory:'" in code
    assert "Base.metadata.create_all(bind=engine)" in code

"""Emit database connection module."""

from openapi_client.models import OpenAPI


def emit_db(spec: OpenAPI) -> str:
    """
    Generate database connection configuration for the server.

    This generates:
    1. Database Connection configuration struct/class.
    2. Connection factory reading DATABASE_URL or EPHEMERAL_DB/flags.
    3. Initialization routine for DB schema migrations.
    """
    lines = [
        '"""Database connection and ephemeral configuration."""',
        "",
        "import os",
        "from typing import Generator, Optional",
        "from sqlalchemy import create_engine, Engine",
        "from sqlalchemy.orm import sessionmaker, Session",
        "from models import Base  # noqa: F401",
        "",
        "class DBConfig:",
        '    """Database Connection configuration class."""',
        "",
        "    def __init__(self, database_url: Optional[str] = None, ephemeral: bool = False):",
        '        """',
        "        Initialize configuration.",
        "        :param database_url: The URL to the database.",
        "        :param ephemeral: If True, override URL to use an ephemeral SQLite database.",
        '        """',
        "        self.ephemeral = ephemeral or os.environ.get('EPHEMERAL_DB', '').lower() in ('true', '1', 'yes')",
        "        if self.ephemeral:",
        "            self.database_url = 'sqlite:///:memory:'",
        "        else:",
        "            self.database_url = database_url or os.environ.get('DATABASE_URL', '')",
        "",
        "def get_engine(config: DBConfig) -> Engine:",
        '    """',
        "    Implement the connection factory.",
        "    Reads the configuration and yields the appropriate SQLAlchemy engine.",
        '    """',
        "    if not config.database_url:",
        "        raise ValueError('No database URL configured and not running in ephemeral mode.')",
        "    ",
        "    # For sqlite in-memory, we need a StaticPool to share connection across threads",
        "    if config.ephemeral:",
        "        from sqlalchemy.pool import StaticPool",
        "        return create_engine(config.database_url, connect_args={'check_same_thread': False}, poolclass=StaticPool)",
        "    ",
        "    return create_engine(config.database_url)",
        "",
        "def init_db(engine: Engine) -> None:",
        '    """',
        "    Implement an initialization routine that programmatically executes DB schema migrations.",
        '    """',
        "    Base.metadata.create_all(bind=engine)",
        "",
        "# Global variables for singleton connection",
        "engine = None",
        "SessionLocal = None",
        "",
        "def setup_database(database_url: Optional[str] = None, ephemeral: bool = False) -> None:",
        '    """Set up the global database connection and run migrations if needed."""',
        "    global engine, SessionLocal",
        "    config = DBConfig(database_url=database_url, ephemeral=ephemeral)",
        "    if not config.database_url and not config.ephemeral:",
        "        # Running in pure stub mode",
        "        return",
        "    engine = get_engine(config)",
        "    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)",
        "    init_db(engine)",
        "",
        "def get_db_session() -> Generator[Session, None, None]:",
        '    """Get a database session generator."""',
        "    global SessionLocal",
        "    if SessionLocal is None:",
        "        raise RuntimeError('Database is not configured. Call setup_database() first.')",
        "    db = SessionLocal()",
        "    try:",
        "        yield db",
        "    finally:",
        "        db.close()",
        "",
    ]

    return "\n".join(lines)

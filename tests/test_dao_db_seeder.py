"""Tests for DAO, database configuration, SQLAlchemy CDD, and Faker seeder generation."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from openapi_client.dao.emit import emit_dao
from openapi_client.db.emit import emit_db
from openapi_client.functions.utils import sanitize_class_name
from openapi_client.models import Components, OpenAPI, Reference, Schema
from openapi_client.seeder.emit import emit_seeder
from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy


def test_emit_dao_empty() -> None:
    """Test emit_dao with empty spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    assert emit_dao(spec) == {}


def test_sanitize_class_name_edge_cases() -> None:
    """Test sanitize_class_name on empty, non-alphanumeric, leading-digit, and hyphenated names."""
    assert sanitize_class_name("") == "Model"
    assert sanitize_class_name("---") == "Model"
    assert sanitize_class_name("123-item") == "_123Item"
    assert sanitize_class_name("Pet-Input") == "PetInput"
    assert sanitize_class_name("User") == "User"


def test_emit_dao_with_models() -> None:
    """Test emit_dao with models including hyphenated schema keys."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "User": Schema(type="object", properties={}),
                "Post": Schema(type="object", properties={}),
                "Pet-Input": Schema(type="object", properties={}),
            }
        ),
    )
    files = emit_dao(spec)

    # Check abstract DAOs
    assert "class AbstractUserDAO(abc.ABC):" in files["dao/abstract_user.py"]
    assert "class AbstractPostDAO(abc.ABC):" in files["dao/abstract_post.py"]
    assert "class AbstractPetInputDAO(abc.ABC):" in files["dao/abstract_pet_input.py"]
    assert "def get_all(self) -> List[Any]:" in files["dao/abstract_user.py"]

    # Check stub DAOs
    assert "class StubUserDAO(AbstractUserDAO):" in files["dao/stub_user.py"]
    assert "class StubPostDAO(AbstractPostDAO):" in files["dao/stub_post.py"]
    assert "raise NotImplementedError()" in files["dao/stub_user.py"]

    # Check concrete DAOs (SQLAlchemy 2.0)
    assert "class ConcreteUserDAO(AbstractUserDAO):" in files["dao/concrete_user.py"]
    assert "class ConcretePostDAO(AbstractPostDAO):" in files["dao/concrete_post.py"]
    assert (
        "return list(self.session.scalars(select(User)).all())"
        in files["dao/concrete_user.py"]
    )
    assert (
        "return list(self.session.scalars(select(Post)).all())"
        in files["dao/concrete_post.py"]
    )
    assert "return self.session.get(User, id)" in files["dao/concrete_user.py"]

    # Check DI routine
    init_code = files["dao/__init__.py"]
    assert (
        "def get_dao(model_name: str, session: Optional[Session] = None, ephemeral: bool = False) -> Any:"
        in init_code
    )
    assert "if model_name == 'User':" in init_code
    assert "return StubUserDAO()" in init_code
    assert "return ConcreteUserDAO(session)" in init_code
    assert "elif model_name == 'Post':" in init_code
    assert "model_name in ('Pet-Input', 'PetInput')" in init_code


def test_emit_db() -> None:
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


def test_emit_seeder_empty() -> None:
    """Test emit_seeder with empty spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    assert emit_seeder(spec) == {}


def test_emit_seeder_with_models() -> None:
    """Test emit_seeder with models, foreign-key topological sorting, and keyword properties."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "Post": Schema(
                    type="object",
                    properties={
                        "id": Schema(type="integer"),
                        "user_id": Schema(type="integer"),
                        "external_id": Schema(type="integer"),
                        "author": Reference(**{"$ref": "#/components/schemas/User"}),
                        "self_ref": Reference(**{"$ref": "#/components/schemas/Post"}),
                        "from": Schema(type="string"),
                    },
                ),
                "User": Schema(
                    type="object",
                    properties={
                        "id": Schema(type="integer"),
                        "email": Schema(type="string"),
                        "name": Schema(type="string"),
                        "phone": Schema(type="string"),
                        "age": Schema(type="integer"),
                        "score": Schema(type="number"),
                        "is_active": Schema(type="boolean"),
                        "other": Schema(type="array"),
                        "some_string": Schema(type="string"),
                        "nullable_string": Schema(type=["string", "null"]),
                    },
                ),
            }
        ),
    )
    code = emit_seeder(spec)

    assert "fake = Faker('en_US')" in code["mocks/factories.py"]
    assert "class EntityPool:" in code["mocks/pool.py"]
    assert "def factory_User(pool: EntityPool) -> User:" in code["mocks/factories.py"]
    assert "obj.email = fake.email()" in code["mocks/factories.py"]
    assert "obj.name = fake.name()" in code["mocks/factories.py"]
    assert "obj.phone = fake.phone_number()" in code["mocks/factories.py"]
    assert "obj.age = random.randint(1, 1000)" in code["mocks/factories.py"]
    assert "obj.score = random.random() * 100" in code["mocks/factories.py"]
    assert "obj.is_active = random.choice([True, False])" in code["mocks/factories.py"]
    assert "obj.other = 'mock_value'" in code["mocks/factories.py"]
    assert "obj.some_string = fake.word()" in code["mocks/factories.py"]
    assert "obj.user_id = pool.get_random('User')" in code["mocks/factories.py"]
    assert "obj.author = pool.get_random('User')" in code["mocks/factories.py"]
    assert "setattr(obj, 'from', fake.word())" in code["mocks/factories.py"]
    assert "def seed_database(session: Session) -> None:" in code["mocks/seeder.py"]
    assert "for _ in range(10):" in code["mocks/seeder.py"]
    assert "obj = factory_User(pool)" in code["mocks/seeder.py"]
    # Verify topological ordering: User is seeded before Post even though Post was declared first
    assert code["mocks/seeder.py"].index("factory_User") < code[
        "mocks/seeder.py"
    ].index("factory_Post")


def _install_sqlite_sqlalchemy_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a stdlib `sqlite3`-backed SQLAlchemy 2.0 and Faker shim into `sys.modules`.

    Args:
        monkeypatch: Pytest MonkeyPatch fixture.
    """
    import sqlite3
    import types

    class Column:
        """Column descriptor recording SQLite type and primary-key metadata."""

        def __init__(
            self,
            col_type: object,
            default: object = None,
            primary_key: bool = False,
            server_default: object = None,
            nullable: bool = True,
        ) -> None:
            """Initialize column descriptor.

            Args:
                col_type: Parameter .
                default: Parameter .
                primary_key: Parameter .
                server_default: Parameter .
                nullable: Parameter .
            """
            self.col_type = col_type
            self.default = default
            self.primary_key = primary_key
            self.server_default = server_default
            self.nullable = nullable

    class _MetaData:
        """Metadata registry that creates real SQLite tables on `create_all`."""

        def __init__(self, registry: list[type]) -> None:
            """Initialize metadata with model class registry.

            Args:
                registry: Parameter .
            """
            self.registry = registry

        def create_all(self, bind: Engine) -> None:
            """Execute CREATE TABLE statements on the bound SQLite connection.

            Args:
                bind: Parameter .
            """
            for cls in self.registry:
                cols_sql: list[str] = []
                for attr, val in getattr(cls, "_columns", {}).items():
                    if val.primary_key:
                        cols_sql.append(f'"{attr}" INTEGER PRIMARY KEY AUTOINCREMENT')
                    else:
                        cols_sql.append(f'"{attr}" TEXT')
                stmt = f'CREATE TABLE IF NOT EXISTS "{cls.__tablename__}" ({", ".join(cols_sql)})'
                bind.conn.execute(stmt)
            bind.conn.commit()

    def declarative_base() -> type:
        """Construct a declarative base class backed by `_MetaData`."""
        registry: list[type] = []

        class BaseMeta(type):
            """Metaclass registering declarative subclasses and initializing Column attributes."""

            def __new__(
                mcs, name: str, bases: tuple[type, ...], namespace: dict[str, object]
            ) -> type:
                """Create model class and record its column definitions."""
                cls = super().__new__(mcs, name, bases, namespace)
                if bases:
                    cols = {k: v for k, v in namespace.items() if isinstance(v, Column)}
                    cls._columns = cols  # type: ignore[attr-defined]
                    for k, col in cols.items():
                        setattr(cls, k, col.default)
                    registry.append(cls)
                return cls

        class Base(metaclass=BaseMeta):
            """Declarative base model."""

            metadata = _MetaData(registry)

            def __init__(self, **kwargs: object) -> None:
                """Initialize model attributes from keyword arguments.

                Args:
                    **kwargs: Parameter .
                """
                for k in getattr(self, "_columns", {}):
                    setattr(self, k, kwargs.get(k, None))
                for k, v in kwargs.items():
                    setattr(self, k, v)

        return Base

    class Engine:
        """SQLite connection wrapper representing a SQLAlchemy Engine."""

        def __init__(self, url: str) -> None:
            """Open an in-memory SQLite connection.

            Args:
                url: Parameter .
            """
            _ = url
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row

    class _ScalarResult:
        """Result wrapper supporting `.all()` for `session.scalars(select(Model))`."""

        def __init__(self, items: list[object]) -> None:
            """Initialize scalar result list.

            Args:
                items: Parameter .
            """
            self._items = items

        def all(self) -> list[object]:
            """Return all hydrated model instances."""
            return list(self._items)

    class Session:
        """SQLite-backed SQLAlchemy 2.0 Session supporting add, commit, refresh, scalars, get, delete."""

        def __init__(self, bind: Engine) -> None:
            """Initialize session bound to `bind`.

            Args:
                bind: Parameter .
            """
            self.bind = bind
            self._pending_adds: list[object] = []
            self._pending_deletes: list[object] = []

        def add(self, obj: object) -> None:
            """Stage an ORM instance for insertion.

            Args:
                obj: Parameter .
            """
            self._pending_adds.append(obj)

        def delete(self, obj: object) -> None:
            """Stage an ORM instance for deletion.

            Args:
                obj: Parameter .
            """
            self._pending_deletes.append(obj)

        def commit(self) -> None:
            """Flush staged inserts and deletes to the SQLite connection."""
            cur = self.bind.conn.cursor()
            for obj in self._pending_adds:
                table = obj.__class__.__tablename__  # type: ignore[attr-defined]
                cols = [
                    k
                    for k in obj.__class__._columns  # type: ignore[attr-defined]
                    if k != "id" or getattr(obj, "id", None) is not None
                ]
                placeholders = ", ".join("?" for _ in cols)
                col_names = ", ".join(f'"{c}"' for c in cols)
                vals = [getattr(obj, c, None) for c in cols]
                cur.execute(
                    f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})',
                    vals,
                )
                if getattr(obj, "id", None) is None:
                    obj.id = cur.lastrowid
            self._pending_adds.clear()

            for obj in self._pending_deletes:
                table = obj.__class__.__tablename__  # type: ignore[attr-defined]
                cur.execute(f'DELETE FROM "{table}" WHERE id = ?', (obj.id,))
            self._pending_deletes.clear()
            self.bind.conn.commit()

        def refresh(self, obj: object) -> None:
            """Refresh an ORM instance from SQLite.

            Args:
                obj: Parameter .
            """
            _ = obj

        def _hydrate(self, model_cls: type, row: sqlite3.Row) -> object:
            """Hydrate a model instance from a SQLite row.

            Args:
                model_cls: Parameter .
                row: Parameter .
            """
            inst = model_cls()
            for k, val in dict(row).items():
                col = model_cls._columns.get(k)  # type: ignore[attr-defined]
                if col and col.col_type is int and val is not None:
                    val = int(val)
                setattr(inst, k, val)
            return inst

        def scalars(self, model_cls: type) -> _ScalarResult:
            """Execute a SELECT query for `model_cls` and return a `_ScalarResult`.

            Args:
                model_cls: Parameter .
            """
            table = model_cls.__tablename__  # type: ignore[attr-defined]
            rows = self.bind.conn.execute(f'SELECT * FROM "{table}"').fetchall()
            return _ScalarResult([self._hydrate(model_cls, r) for r in rows])

        def get(self, model_cls: type, ident: object) -> object | None:
            """Fetch a single instance of `model_cls` by primary key.

            Args:
                model_cls: Parameter .
                ident: Parameter .
            """
            table = model_cls.__tablename__  # type: ignore[attr-defined]
            row = self.bind.conn.execute(
                f'SELECT * FROM "{table}" WHERE id = ?', (ident,)
            ).fetchone()
            return self._hydrate(model_cls, row) if row is not None else None

        def close(self) -> None:
            """Close the session."""

    sa_mod = types.ModuleType("sqlalchemy")
    sa_mod.Column = Column  # type: ignore[attr-defined]
    sa_mod.Integer = int  # type: ignore[attr-defined]
    sa_mod.String = str  # type: ignore[attr-defined]
    sa_mod.Float = float  # type: ignore[attr-defined]
    sa_mod.Boolean = bool  # type: ignore[attr-defined]
    sa_mod.JSON = dict  # type: ignore[attr-defined]
    sa_mod.Identity = lambda: None  # type: ignore[attr-defined]
    sa_mod.Engine = Engine  # type: ignore[attr-defined]
    sa_mod.create_engine = lambda url, **kw: Engine(url)  # type: ignore[attr-defined]
    sa_mod.select = lambda model_cls: model_cls  # type: ignore[attr-defined]

    sa_orm = types.ModuleType("sqlalchemy.orm")
    sa_orm.declarative_base = declarative_base  # type: ignore[attr-defined]
    sa_orm.Session = Session  # type: ignore[attr-defined]
    sa_orm.sessionmaker = lambda bind=None, **kw: lambda: Session(bind)  # type: ignore[attr-defined]

    sa_pool = types.ModuleType("sqlalchemy.pool")
    sa_pool.StaticPool = object  # type: ignore[attr-defined]

    faker_mod = types.ModuleType("faker")

    class Faker:
        """Deterministic Faker stub for tests."""

        def __init__(self, locale: str = "en_US") -> None:
            """Initialize Faker stub.

            Args:
                locale: Parameter .
            """
            self.locale = locale

        def email(self) -> str:
            """Return fake email."""
            return "user@example.com"

        def name(self) -> str:
            """Return fake name."""
            return "Test User"

        def phone_number(self) -> str:
            """Return fake phone number."""
            return "555-0100"

        def word(self) -> str:
            """Return fake word."""
            return "sample"

    faker_mod.Faker = Faker  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "sqlalchemy", sa_mod)
    monkeypatch.setitem(sys.modules, "sqlalchemy.orm", sa_orm)
    monkeypatch.setitem(sys.modules, "sqlalchemy.pool", sa_pool)
    monkeypatch.setitem(sys.modules, "faker", faker_mod)


def test_execute_generated_dao_db_seeder_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Execute generated SQLAlchemy models, DAOs, db.py, and seeder.py against SQLite in-memory.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """
    _install_sqlite_sqlalchemy_shim(monkeypatch)
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "Post": Schema(
                    type="object",
                    properties={
                        "id": Schema(type="integer"),
                        "user_id": Schema(type="integer"),
                        "title": Schema(type="string"),
                    },
                ),
                "User": Schema(
                    type="object",
                    properties={
                        "id": Schema(type="integer"),
                        "name": Schema(type="string"),
                        "email": Schema(type="string"),
                    },
                ),
            }
        ),
    )

    files: dict[str, str] = {}
    files.update(emit_sqlalchemy(spec))
    files.update(emit_dao(spec))
    files["db.py"] = emit_db(spec)
    files.update(emit_seeder(spec))

    for rel_path, content in files.items():
        full_path = tmp_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EPHEMERAL_DB", raising=False)

    for mod_name in ("models", "db", "dao", "mocks", "seeder"):
        for loaded in list(sys.modules):
            if loaded == mod_name or loaded.startswith(f"{mod_name}."):
                sys.modules.pop(loaded, None)

    db_mod = importlib.import_module("db")
    dao_mod = importlib.import_module("dao")
    models_mod = importlib.import_module("models")
    seeder_mod = importlib.import_module("seeder")

    # 1. Stub DAO mode raises NotImplementedError
    stub_dao = dao_mod.get_dao("User")
    with pytest.raises(NotImplementedError):
        stub_dao.get_all()
    with pytest.raises(NotImplementedError):
        stub_dao.get_by_id(1)
    with pytest.raises(NotImplementedError):
        stub_dao.create(None)
    with pytest.raises(NotImplementedError):
        stub_dao.delete(1)

    with pytest.raises(ValueError, match="Unknown model"):
        dao_mod.get_dao("NonExistent")
    with pytest.raises(ValueError, match="Session is required"):
        dao_mod.get_dao("User", session=None, ephemeral=True)
    with pytest.raises(ValueError, match="Unknown model"):
        dao_mod.get_dao("NonExistent", session=object(), ephemeral=True)

    # 2. Ephemeral SQLite initialization & seeding
    db_mod.setup_database(ephemeral=True)
    gen = db_mod.get_db_session()
    session = next(gen)
    try:
        seeder_mod.seed_database(session)
        user_dao = dao_mod.get_dao("User", session=session, ephemeral=True)
        post_dao = dao_mod.get_dao("Post", session=session, ephemeral=True)

        users = user_dao.get_all()
        posts = post_dao.get_all()
        assert len(users) == 10
        assert len(posts) == 10
        user_ids = {u.id for u in users}
        assert all(p.user_id in user_ids for p in posts)

        # 3. Create, get_by_id, and delete via ConcreteDAO
        new_user = models_mod.User(name="Alice", email="alice@example.com")
        created = user_dao.create(new_user)
        assert created.id is not None
        fetched = user_dao.get_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Alice"

        assert user_dao.delete(created.id) is True
        assert user_dao.get_by_id(created.id) is None
        assert user_dao.delete(999999) is False
    finally:
        gen.close()

    for mod_name in ("models", "db", "dao", "mocks", "seeder"):
        for loaded in list(sys.modules):
            if loaded == mod_name or loaded.startswith(f"{mod_name}."):
                sys.modules.pop(loaded, None)

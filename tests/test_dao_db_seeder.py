"""Tests for DAO, database configuration, SQLAlchemy CDD, and Faker seeder generation."""

from __future__ import annotations

from openapi_client.dao.emit import emit_dao
from openapi_client.models import OpenAPI, Components, Schema
from openapi_client.db.emit import emit_db
from openapi_client.seeder.emit import emit_seeder


def test_emit_dao_empty():
    """Test emit_dao with empty spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    assert emit_dao(spec) == {}


def test_emit_dao_with_models():
    """Test emit_dao with models."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "User": Schema(type="object", properties={}),
                "Post": Schema(type="object", properties={}),
            }
        ),
    )
    files = emit_dao(spec)

    # Check abstract DAOs
    assert "class AbstractUserDAO(abc.ABC):" in files["dao/abstract_user.py"]
    assert "class AbstractPostDAO(abc.ABC):" in files["dao/abstract_post.py"]
    assert "def get_all(self) -> List[Any]:" in files["dao/abstract_user.py"]

    # Check stub DAOs
    assert "class StubUserDAO(AbstractUserDAO):" in files["dao/stub_user.py"]
    assert "class StubPostDAO(AbstractPostDAO):" in files["dao/stub_post.py"]
    assert "raise NotImplementedError()" in files["dao/stub_user.py"]

    # Check concrete DAOs
    assert "class ConcreteUserDAO(AbstractUserDAO):" in files["dao/concrete_user.py"]
    assert "class ConcretePostDAO(AbstractPostDAO):" in files["dao/concrete_post.py"]
    assert "return self.session.query(User).all()" in files["dao/concrete_user.py"]
    assert "return self.session.query(Post).all()" in files["dao/concrete_post.py"]

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


def test_emit_seeder_empty():
    """Test emit_seeder with empty spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    assert emit_seeder(spec) == {}


def test_emit_seeder_with_models():
    """Test emit_seeder with models."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
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
    assert "def seed_database(session: Session) -> None:" in code["mocks/seeder.py"]
    assert "for _ in range(10):" in code["mocks/seeder.py"]
    assert "obj = factory_User(pool)" in code["mocks/seeder.py"]

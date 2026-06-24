"""Test for seeder generation."""

from openapi_client.seeder.emit import emit_seeder
from openapi_client.models import OpenAPI, Components, Schema


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

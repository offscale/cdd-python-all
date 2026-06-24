"""Test for DAO generation."""

from openapi_client.dao.emit import emit_dao
from openapi_client.models import OpenAPI, Components, Schema


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

"""Emit server tests module."""

from openapi_client.models import OpenAPI


def emit_server_tests(spec: OpenAPI) -> dict[str, str]:
    """
    Generate the test suite for the server, fulfilling Phase 7 categories.
    """
    if not spec.components or not spec.components.schemas:
        return {}

    files = {}

    schemas = spec.components.schemas
    first_model = list(schemas.keys())[0] if schemas else "Dummy"

    # conftest.py
    conftest_lines = [
        "import os",
        "import pytest",
        "from fastapi.testclient import TestClient",
        "from sqlalchemy import create_engine",
        "from sqlalchemy.orm import sessionmaker",
        "",
        "from main import app",
        "from db import Base, setup_database, get_db_session",
        "from dao import get_dao",
        "from seeder import EntityPool, seed_database",
        "import models",
        "",
        "@pytest.fixture",
        "def client():",
        "    return TestClient(app)",
        "",
        "@pytest.fixture",
        "def ephemeral_client():",
        '    """Fixture to provide a client with an ephemeral clean database."""',
        "    setup_database(ephemeral=True)",
        "    gen = get_db_session()",
        "    db = next(gen)",
        "    for table in reversed(Base.metadata.sorted_tables):",
        "        db.execute(table.delete())",
        "    db.commit()",
        "    db.close()",
        "    with TestClient(app) as client:",
        "        yield client",
        "",
        "@pytest.fixture",
        "def seeded_client():",
        '    """Fixture to provide a seeded ephemeral database."""',
        "    setup_database(ephemeral=True)",
        "    gen = get_db_session()",
        "    db = next(gen)",
        "    for table in reversed(Base.metadata.sorted_tables):",
        "        db.execute(table.delete())",
        "    db.commit()",
        "    seed_database(db)",
        "    db.close()",
        "    with TestClient(app) as client:",
        "        yield client",
        "",
    ]
    files["conftest.py"] = "\n".join(conftest_lines)

    # test_unit.py
    unit_lines = [
        "import os",
        "from unittest.mock import patch",
        "from db import setup_database, get_db_session",
        "from dao import get_dao",
        "from seeder import EntityPool",
        "",
        "def test_db_config_ephemeral():",
        '    """Test that DB config properly routes ephemeral flag."""',
        "    setup_database(ephemeral=True)",
        "    gen = get_db_session()",
        "    db = next(gen)",
        "    assert db is not None",
        "    db.close()",
        "",
        "@patch.dict(os.environ, {}, clear=True)",
        "def test_dao_factory_stub():",
        '    """Test DAO factory returns Stubs when no DB."""',
        f"    dao = get_dao('{first_model}')",
        f"    assert type(dao).__name__ == 'Stub{first_model}DAO'",
        "",
        "def test_dao_factory_concrete():",
        '    """Test DAO factory returns Concrete DAOs when DB is available."""',
        "    setup_database(ephemeral=True)",
        "    gen = get_db_session()",
        "    db = next(gen)",
        f"    dao = get_dao('{first_model}', session=db, ephemeral=True)",
        f"    assert type(dao).__name__ == 'Concrete{first_model}DAO'",
        "    db.close()",
        "",
        "def test_seeder_referential_integrity():",
        '    """Test seeder populates the Entity Pool correctly."""',
        "    pool = EntityPool()",
        f"    pool.add('{first_model}', 1)",
        f"    assert pool.get_random('{first_model}') == 1",
        "    assert pool.get_random('NonExistent') is None",
        "",
    ]
    files["test_unit.py"] = "\n".join(unit_lines)

    # test_stub.py
    stub_lines = [
        "from fastapi.testclient import TestClient",
        "from main import app",
        "",
        "def test_stub_endpoints():",
        '    """Test that endpoints return NotImplemented safely in stub mode."""',
        "    client = TestClient(app)",
    ]
    test_path = ""
    if spec.paths:
        for path, path_item in spec.paths.items():
            if getattr(path_item, "get", None):
                test_path = path.replace("{", "").replace("}", "")
                break

    if test_path:
        stub_lines.extend(
            [
                f"    response = client.get('{test_path}')",
                "    assert response.status_code == 200",
                "    assert 'Not implemented' in response.text",
                "",
            ]
        )
    else:
        stub_lines.extend(["    pass # No GET endpoints found in spec", ""])
    files["test_stub.py"] = "\n".join(stub_lines)

    # test_ephemeral.py
    ephemeral_lines = [
        "from dao import get_dao",
        "from db import get_db_session",
        "",
        "def test_ephemeral_clean_state(ephemeral_client):",
        '    """Test that the ephemeral DB is clean initially."""',
        "    gen = get_db_session()",
        "    db = next(gen)",
        f"    dao = get_dao('{first_model}', session=db, ephemeral=True)",
        "    items = dao.get_all()",
        "    assert len(items) == 0",
        "    db.close()",
        "",
    ]
    files["test_ephemeral.py"] = "\n".join(ephemeral_lines)

    # test_seeded.py
    seeded_lines = [
        "from dao import get_dao",
        "from db import get_db_session",
        "",
        "def test_seeded_state(seeded_client):",
        '    """Test that the seeded DB contains generated relational data."""',
        "    gen = get_db_session()",
        "    db = next(gen)",
        f"    dao = get_dao('{first_model}', session=db, ephemeral=True)",
        "    items = dao.get_all()",
        "    assert len(items) > 0",
        "    db.close()",
        "",
    ]
    files["test_seeded.py"] = "\n".join(seeded_lines)

    # test_advanced.py
    advanced_lines = [
        "from fastapi.testclient import TestClient",
        "from main import app",
        "",
        "def test_cors_preflight():",
        '    """Test CORS preflight and cross-origin requests."""',
        "    with TestClient(app) as client:",
        "        response = client.options('/_mock/trigger-webhook/test', headers={'Origin': 'http://localhost', 'Access-Control-Request-Method': 'POST'})",
        "        assert response.status_code == 200",
        "        assert response.headers.get('access-control-allow-origin') in ('*', 'http://localhost')",
        "",
        "def test_strict_validation_mock():",
        '    """Test strict validation intercept (stub)."""',
        "    from main import config_flags",
        "    config_flags['strict_validation'] = True",
        "    with TestClient(app) as client:",
        "        client.get('/')",
        "    config_flags['strict_validation'] = False",
        "",
        "def test_auth_enforcement_mock():",
        '    """Test that protected endpoints return 401 when auth enforced."""',
        "    from main import config_flags",
        "    config_flags['enforce_auth'] = True",
        "    with TestClient(app) as client:",
        "        response = client.get('/')",
        "        assert response.status_code == 401",
        "        response = client.get('/', headers={'Authorization': 'Bearer mock-token-123'})",
        "        assert response.status_code != 401",
        "    config_flags['enforce_auth'] = False",
        "",
        "def test_trigger_webhook():",
        '    """Test administrative webhook trigger."""',
        "    with TestClient(app) as client:",
        "        response = client.post('/_mock/trigger-webhook/test_hook')",
        "        assert response.status_code == 200",
        "        assert response.json()['webhook_name'] == 'test_hook'",
        "",
        "def test_auth_endpoints_mock():",
        '    """Test Identity Provider endpoints."""',
        "    with TestClient(app) as client:",
        "        response = client.post('/auth/register')",
        "        assert response.status_code == 200",
        "        assert 'token' in response.json()",
        "        response = client.post('/auth/login')",
        "        assert response.status_code == 200",
        "        assert 'token' in response.json()",
        "        response = client.post('/auth/refresh')",
        "        assert response.status_code == 200",
        "        assert 'token' in response.json()",
        "        response = client.post('/auth/logout')",
        "        assert response.status_code == 200",
        "",
    ]
    files["test_advanced.py"] = "\n".join(advanced_lines)

    return files

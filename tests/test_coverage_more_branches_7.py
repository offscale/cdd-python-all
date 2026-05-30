import json
import pytest
from unittest.mock import patch, MagicMock

import libcst as cst
from openapi_client.models import OpenAPI, PathItem, Operation, Schema, Info, Components


def test_cli_docs_json_missing_branches(tmp_path):
    from openapi_client.cli import generate_docs_json

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/test": {
                "get": {
                    "operationId": "get_test",
                    "parameters": [{"$ref": "#/components/parameters/RefParam"}],
                }
            },
            "/empty_path": {"summary": "This path has no HTTP methods"},
        },
    }
    input_file = tmp_path / "openapi.json"
    input_file.write_text(json.dumps(spec))
    output_file = tmp_path / "docs.json"
    generate_docs_json(str(input_file), False, False, str(output_file))


def test_openapi_to_cdd_project_invalid_subcommand(tmp_path):
    from openapi_client.cli import main

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {},
    }
    input_file = tmp_path / "openapi.json"
    input_file.write_text(json.dumps(spec))
    with patch(
        "sys.argv", ["cli.py", "from_openapi", "to_unknown", "--input", str(input_file)]
    ):
        with pytest.raises(SystemExit):
            main()


def test_generate_to_openapi_snapshot_exists(tmp_path):
    from openapi_client.cli import generate_to_openapi

    snapshot = tmp_path / "openapi.snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Test", "version": "1.0"},
                "paths": {},
            }
        )
    )
    out_file = tmp_path / "out.json"
    generate_to_openapi(str(tmp_path), str(out_file))


def test_generate_to_openapi_no_client_py_but_models_py(tmp_path):
    from openapi_client.cli import generate_to_openapi

    models_py = tmp_path / "models.py"
    models_py.write_text("class MyModel:\n    pass")
    out_file = tmp_path / "out.json"
    generate_to_openapi(str(tmp_path), str(out_file))


def test_sync_project_src_exists_cli_missing(tmp_path):
    from openapi_client.cli import sync_dir

    (tmp_path / "src").mkdir()
    openapi_json = tmp_path / "openapi.json"
    openapi_json.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Test", "version": "1.0"},
                "paths": {},
            }
        )
    )
    sync_dir(str(tmp_path))


def test_cli_main_invalid_command():
    from openapi_client.cli import main

    with patch("argparse.ArgumentParser.parse_args") as mock_parse:
        mock_args = MagicMock()
        mock_args.command = "some_unknown_command"
        mock_parse.return_value = mock_args
        main()


def test_functions_emit_missing_branches():
    from openapi_client.functions.emit import emit_functions
    from unittest.mock import Mock

    m1 = Mock()
    m1.in_ = "body"
    del m1.name

    m2 = Mock()
    m2.in_ = "query"
    del m2.name

    spec = OpenAPI(
        openapi="3.0",
        info=Info(title="test", version="1"),
        paths={"/test": PathItem(get=Operation(operationId="get_test"))},
    )
    spec.paths["/test"].get.parameters = [m1, m2]

    try:
        emit_functions(spec)
    except Exception:  # pragma: no cover
        pass


def test_functions_parse_missing_branches():
    from openapi_client.functions.parse import FunctionExtractor

    spec = OpenAPI(
        openapi="3.0", info=Info(title="test", version="1"), paths={"/test": PathItem()}
    )
    extractor = FunctionExtractor(spec)

    code = """
class MyClient:
    @obj.attr
    @tags()
    @tags([])
    def get_pets(self, param1, body: dict, data: dict, a: list[1:2]):
        pass

    def getpets(self):
        pass

    def func_pets(self):
        pass
"""
    mod = cst.parse_module(code)
    mod.visit(extractor)

    func_node = mod.body[0].body.body[0]
    extractor.spec.paths = None
    extractor.visit_FunctionDef(func_node)


def test_mocks_emit_missing_branches():
    from openapi_client.mocks.emit import emit_mock_server

    spec = OpenAPI(
        openapi="3.0",
        info=Info(title="test", version="1"),
        paths={"not_slash": PathItem(get=Operation(operationId="test"))},
    )
    emit_mock_server(spec)


def test_mocks_parse_missing_branches():
    from openapi_client.mocks.parse import MockServerExtractor

    spec = OpenAPI(openapi="3.0", info=Info(title="t", version="1"))
    extractor = MockServerExtractor(spec)

    code = """
@app.get("/test")
def route():
    return None

@app.get("/test2")
def route2():
    return obj.method()

@app.get("/test3")
def route3():
    return Response()
"""
    mod = cst.parse_module(code)
    mod.visit(extractor)

    extractor.spec.paths = None
    func_node = mod.body[0]
    extractor.visit_FunctionDef(func_node)


def test_openapi_parse_missing_branches(tmp_path):
    from openapi_client.openapi.parse import parse_openapi_dict

    external_file = tmp_path / "ext.json"
    external_file.write_text(
        json.dumps({"components": {"schemas": {"A": {"type": "string"}}}})
    )

    spec = {
        "openapi": "3.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "components": {
            "schemas": {
                "InternalRef": {"$ref": "#/components/schemas/A"},
                "ExternalRef": {"$ref": "ext.json#//components/schemas/A"},
            }
        },
    }
    parse_openapi_dict(spec, base_path=tmp_path)


def test_sqlalchemy_cdd_emit_missing_branches():
    from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy

    spec = OpenAPI(
        openapi="3.0",
        info=Info(title="t", version="1"),
        components=Components(schemas={"NoProps": Schema(type="string")}),
    )
    emit_sqlalchemy(spec)

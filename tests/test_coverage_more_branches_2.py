import libcst as cst
from openapi_client.models import OpenAPI, PathItem, Operation, Parameter
from openapi_client.cli_sdk.parse import extract_cli_from_ast


def test_cli_sdk_parse_branches():
    code = """
parser.add_parser(var)
parser.add_argument(var)
parser.add_argument("positional", help="desc")
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})

    spec.paths = {
        "/test1": PathItem(
            get=Operation(
                operationId="test1",
                responses={},
                parameters=[Parameter(name="myarg", **{"in": "query"})],
            )
        )
    }
    extract_cli_from_ast(module, spec)

    code2 = """
parser.add_parser("not_found")
parser.add_parser("test1", help="desc")
parser.add_argument("--other", help="desc")
parser.add_argument("--myarg", help="desc")
"""
    module2 = cst.parse_module(code2)
    extract_cli_from_ast(module2, spec)

    code3 = """
parser.add_parser("test2")
parser.add_argument("--noparams", help="desc")
"""
    spec.paths["/test2"] = PathItem(
        get=Operation(operationId="test2", responses={}, parameters=[])
    )
    module3 = cst.parse_module(code3)
    extract_cli_from_ast(module3, spec)


def test_cli_sdk_parse_branches_58_exit():
    code = """
parser.add_parser("test1")
parser.add_argument("positional", help="desc")
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    spec.paths = {
        "/test1": PathItem(
            get=Operation(operationId="test1", responses={}, parameters=[])
        )
    }
    extract_cli_from_ast(module, spec)

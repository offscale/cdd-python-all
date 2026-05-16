from openapi_client.functions.utils import sanitize_name


def test_sanitize_name():
    """Test sanitizing python identifiers."""
    assert sanitize_name("list-data-sets") == "list_data_sets"
    assert sanitize_name("find pet by id") == "find_pet_by_id"
    assert sanitize_name("1invalid") == "_1invalid"
    assert sanitize_name("valid_name") == "valid_name"
    assert sanitize_name("") == ""

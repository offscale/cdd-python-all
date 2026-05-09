import libcst as cst
from openapi_client.classes.emit import emit_class
from openapi_client.models import Schema, Reference

def test_emit_class_with_reference():
    schema = Schema(
        type="object",
        properties={
            "my_ref": Reference(ref="#/components/schemas/Pet")
        }
    )
    class_def = emit_class("MyModel", schema)
    assert isinstance(class_def, cst.ClassDef)
    assert class_def.name.value == "MyModel"

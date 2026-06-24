"""Emit fake data seeder module."""

from openapi_client.models import OpenAPI


def emit_seeder(spec: OpenAPI) -> dict[str, str]:
    """
    Generate the data seeder for the server using Faker in a modular way.
    """
    if not spec.components or not spec.components.schemas:
        return {}

    files = {}

    # mocks/pool.py
    pool_lines = [
        "from typing import Any, Dict, List",
        "",
        "class EntityPool:",
        '    """',
        "    Entity Pool to cache IDs of successfully generated records.",
        "    Ensures referential integrity by providing valid parent IDs.",
        '    """',
        "    def __init__(self):",
        '        """Initialize the entity pool."""',
        "        self.pools: Dict[str, List[Any]] = {}",
        "",
        "    def add(self, model_name: str, entity_id: Any) -> None:",
        '        """Add an entity ID to the pool."""',
        "        if model_name not in self.pools:",
        "            self.pools[model_name] = []",
        "        self.pools[model_name].append(entity_id)",
        "",
        "    def get_random(self, model_name: str) -> Any:",
        '        """Get a random entity ID from the pool."""',
        "        if model_name not in self.pools or not self.pools[model_name]:",
        "            return None",
        "        import random",
        "        return random.choice(self.pools[model_name])",
        "",
    ]
    files["mocks/pool.py"] = "\n".join(pool_lines)

    schemas = spec.components.schemas
    model_names = list(schemas.keys())

    # mocks/factories.py
    factories_lines = [
        "import random",
        "from faker import Faker",
        "from .pool import EntityPool",
        "from models import *  # noqa: F403",
        "",
        "fake = Faker('en_US')",
        "",
    ]

    for name in model_names:
        factories_lines.extend(
            [
                f"def factory_{name}(pool: EntityPool) -> {name}:",
                '    """',
                f"    Create a mapping dictionary for {name} using Faker.",
                "    Uses pool to randomly select valid foreign keys if needed.",
                '    """',
                f"    obj = {name}()",
            ]
        )

        schema = schemas[name]
        if hasattr(schema, "properties") and schema.properties:
            for prop_name, prop in schema.properties.items():
                p_type = getattr(prop, "type", "string")
                if isinstance(p_type, list):
                    p_type = p_type[0]

                if p_type == "string":
                    if "email" in prop_name.lower():
                        factories_lines.append(f"    obj.{prop_name} = fake.email()")
                    elif "name" in prop_name.lower():
                        factories_lines.append(f"    obj.{prop_name} = fake.name()")
                    elif "phone" in prop_name.lower():
                        factories_lines.append(
                            f"    obj.{prop_name} = fake.phone_number()"
                        )
                    else:
                        factories_lines.append(f"    obj.{prop_name} = fake.word()")
                elif p_type == "integer":
                    if prop_name.lower() == "id":
                        factories_lines.append("    # obj.id = ...")
                    else:
                        factories_lines.append(
                            f"    obj.{prop_name} = random.randint(1, 1000)"
                        )
                elif p_type == "number":
                    factories_lines.append(
                        f"    obj.{prop_name} = random.random() * 100"
                    )
                elif p_type == "boolean":
                    factories_lines.append(
                        f"    obj.{prop_name} = random.choice([True, False])"
                    )
                else:
                    factories_lines.append(f"    obj.{prop_name} = 'mock_value'")

        factories_lines.extend(["    return obj", ""])

    files["mocks/factories.py"] = "\n".join(factories_lines)

    # mocks/seeder.py
    seeder_lines = [
        "from sqlalchemy.orm import Session",
        "from .pool import EntityPool",
        "from .factories import *  # noqa: F403",
        "",
        "def seed_database(session: Session) -> None:",
        '    """',
        "    Batch insertion function to seed the database.",
        "    Maintains topological order and generation ratios.",
        '    """',
        "    pool = EntityPool()",
        "",
    ]

    for name in model_names:
        seeder_lines.extend(
            [
                f"    # Seed {name}",
                "    for _ in range(10):",
                f"        obj = factory_{name}(pool)",
                "        session.add(obj)",
                "        session.commit()",
                "        session.refresh(obj)",
                "        if hasattr(obj, 'id'):",
                f"            pool.add('{name}', obj.id)",
                "",
            ]
        )

    files["mocks/seeder.py"] = "\n".join(seeder_lines)

    files["mocks/__init__.py"] = (
        "from .pool import EntityPool\nfrom .seeder import seed_database\n"
    )
    # Also provide a top-level seeder.py backward compatible shim so other parts of code still work
    files["seeder.py"] = (
        "from mocks.pool import EntityPool\nfrom mocks.seeder import seed_database\n"
    )

    return files

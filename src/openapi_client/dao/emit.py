"""Emit DAO module."""

from openapi_client.models import OpenAPI


def emit_dao(spec: OpenAPI) -> dict[str, str]:
    """
    Generate Data Access Object (DAO) classes from an OpenAPI specification.

    This generates composable files:
    1. Abstract DAO interfaces.
    2. Stub DAOs (returning NotImplementedError).
    3. Concrete DAOs (using SQLAlchemy).
    4. A Dependency Injection/Factory routine.
    """
    if not spec.components or not spec.components.schemas:
        return {}

    files = {}
    init_lines = [
        '"""DAO factory module."""',
        "",
        "import os",
        "from typing import Any, Optional",
        "from sqlalchemy.orm import Session",
        "",
    ]

    schemas = spec.components.schemas

    for name in schemas.keys():
        lower_name = name.lower()

        # 1. Abstract DAOs
        abstract_lines = [
            f'"""Abstract DAO for {name}."""',
            "",
            "import abc",
            "from typing import Any, List, Optional",
            "",
            f"class Abstract{name}DAO(abc.ABC):",
            f'    """Abstract interface for {name} data access."""',
            "",
            "    @abc.abstractmethod",
            "    def get_all(self) -> List[Any]:",
            f'        """Get all {name}s."""',
            "        pass",
            "",
            "    @abc.abstractmethod",
            "    def get_by_id(self, id: Any) -> Optional[Any]:",
            f'        """Get {name} by ID."""',
            "        pass",
            "",
            "    @abc.abstractmethod",
            "    def create(self, data: Any) -> Any:",
            f'        """Create a new {name}."""',
            "        pass",
            "",
            "    @abc.abstractmethod",
            "    def delete(self, id: Any) -> bool:",
            f'        """Delete a {name} by ID."""',
            "        pass",
            "",
        ]
        files[f"dao/abstract_{lower_name}.py"] = "\n".join(abstract_lines)

        # 2. Stub DAOs
        stub_lines = [
            f'"""Stub DAO for {name}."""',
            "",
            "from typing import Any, List, Optional",
            f"from .abstract_{lower_name} import Abstract{name}DAO",
            "",
            f"class Stub{name}DAO(Abstract{name}DAO):",
            f'    """Stub implementation for {name} data access."""',
            "",
            "    def get_all(self) -> List[Any]:",
            f'        """Get all {name}s."""',
            "        raise NotImplementedError()",
            "",
            "    def get_by_id(self, id: Any) -> Optional[Any]:",
            f'        """Get {name} by ID."""',
            "        raise NotImplementedError()",
            "",
            "    def create(self, data: Any) -> Any:",
            f'        """Create a new {name}."""',
            "        raise NotImplementedError()",
            "",
            "    def delete(self, id: Any) -> bool:",
            f'        """Delete a {name} by ID."""',
            "        raise NotImplementedError()",
            "",
        ]
        files[f"dao/stub_{lower_name}.py"] = "\n".join(stub_lines)

        # 3. Concrete DAOs
        concrete_lines = [
            f'"""Concrete DAO for {name}."""',
            "",
            "from typing import Any, List, Optional",
            "from sqlalchemy.orm import Session",
            f"from .abstract_{lower_name} import Abstract{name}DAO",
            f"from models import {name}",
            "",
            f"class Concrete{name}DAO(Abstract{name}DAO):",
            f'    """Concrete SQLAlchemy implementation for {name} data access."""',
            "",
            "    def __init__(self, session: Session):",
            f'        """Initialize the concrete {name} DAO."""',
            "        self.session = session",
            "",
            "    def get_all(self) -> List[Any]:",
            f'        """Get all {name}s."""',
            f"        return self.session.query({name}).all()",
            "",
            "    def get_by_id(self, id: Any) -> Optional[Any]:",
            f'        """Get {name} by ID."""',
            f"        return self.session.query({name}).get(id)",
            "",
            "    def create(self, data: Any) -> Any:",
            f'        """Create a new {name}."""',
            "        self.session.add(data)",
            "        self.session.commit()",
            "        self.session.refresh(data)",
            "        return data",
            "",
            "    def delete(self, id: Any) -> bool:",
            f'        """Delete a {name} by ID."""',
            "        obj = self.get_by_id(id)",
            "        if obj:",
            "            self.session.delete(obj)",
            "            self.session.commit()",
            "            return True",
            "        return False",
            "",
        ]
        files[f"dao/concrete_{lower_name}.py"] = "\n".join(concrete_lines)

        # Add to init
        init_lines.append(f"from .stub_{lower_name} import Stub{name}DAO")
        init_lines.append(f"from .concrete_{lower_name} import Concrete{name}DAO")

    # 4. Dependency Injection Routine
    init_lines.extend(
        [
            "",
            "def get_dao(model_name: str, session: Optional[Session] = None, ephemeral: bool = False) -> Any:",
            '    """',
            "    Factory routine to resolve the correct DAO.",
            "    Fallback: If no DATABASE_URL and no --ephemeral, return Stub DAOs.",
            "    Active: Otherwise, return Concrete DAOs.",
            '    """',
            "    has_db = bool(os.environ.get('DATABASE_URL')) or ephemeral",
            "    if not has_db:",
        ]
    )

    for i, name in enumerate(schemas.keys()):
        if i == 0:
            init_lines.append(f"        if model_name == '{name}':")
        else:
            init_lines.append(f"        elif model_name == '{name}':")
        init_lines.append(f"            return Stub{name}DAO()")

    init_lines.extend(
        [
            "        else:",
            "            raise ValueError(f'Unknown model: {model_name}')",
            "    else:",
            "        if session is None:",
            "            raise ValueError('Session is required for Concrete DAOs')",
        ]
    )

    for i, name in enumerate(schemas.keys()):
        if i == 0:
            init_lines.append(f"        if model_name == '{name}':")
        else:
            init_lines.append(f"        elif model_name == '{name}':")
        init_lines.append(f"            return Concrete{name}DAO(session)")

    init_lines.extend(
        [
            "        else:",
            "            raise ValueError(f'Unknown model: {model_name}')",
            "",
        ]
    )

    files["dao/__init__.py"] = "\n".join(init_lines)

    return files

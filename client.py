from urllib3 import PoolManager
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.http = PoolManager()

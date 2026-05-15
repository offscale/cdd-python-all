import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from client import Client

@pytest.fixture
def client():
    return Client(os.getenv("API_URL", "http://localhost:8080/v2"))


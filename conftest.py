import pytest
from application import app


@pytest.fixture
def client():
    app.config["TESTING"] = True  # Set TESTING flag to True for testing mode
    with app.test_client() as client:
        yield client

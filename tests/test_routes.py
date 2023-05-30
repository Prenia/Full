from flask import session
import pytest
from application import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    expected_text = "Streamlining Communication for Shared Living Spaces"
    assert expected_text.encode() in response.data



def test_login(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_register(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Register" in response.data



if __name__ == "__main__":
    pytest.main()

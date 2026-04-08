"""FastAPI endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from tomodachai.api.routes import set_game_state
from tomodachai.config import AppConfig, LLMConfig, LocationConfig, SimulationConfig
from tomodachai.game_state import GameState
from tomodachai.server import create_app


@pytest.fixture
def app():
    """Create a test app with in-memory game state."""
    application = create_app()
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def seeded_client(client):
    """Client with 2 characters pre-loaded."""
    client.post("/api/characters", json={
        "id": "char_1",
        "name": "민수",
        "personality_code": "outgoing_dynamo",
        "backstory": "활발한 청년",
        "birthday": "03-15",
        "blood_type": "B",
        "gender": "남성",
        "speech_habits": {"normal": "~인 거지"},
    })
    client.post("/api/characters", json={
        "id": "char_2",
        "name": "지은",
        "personality_code": "easygoing_dreamer",
        "backstory": "몽상가",
        "birthday": "11-02",
        "blood_type": "A",
        "gender": "여성",
        "speech_habits": {"normal": "그치~?"},
    })
    return client


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def test_status(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["characters"] == 0


# ---------------------------------------------------------------------------
# Characters CRUD
# ---------------------------------------------------------------------------

def test_create_character(client):
    resp = client.post("/api/characters", json={
        "id": "char_1",
        "name": "민수",
        "personality_code": "outgoing_dynamo",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "민수"
    assert data["personality_code"] == "outgoing_dynamo"


def test_create_duplicate_character(client):
    client.post("/api/characters", json={
        "id": "char_1", "name": "민수", "personality_code": "outgoing_dynamo",
    })
    resp = client.post("/api/characters", json={
        "id": "char_1", "name": "민수2", "personality_code": "outgoing_dynamo",
    })
    assert resp.status_code == 409


def test_list_characters(seeded_client):
    resp = seeded_client.get("/api/characters")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_character(seeded_client):
    resp = seeded_client.get("/api/characters/char_1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "민수"


def test_get_character_not_found(client):
    resp = client.get("/api/characters/nonexistent")
    assert resp.status_code == 404


def test_delete_character(seeded_client):
    resp = seeded_client.delete("/api/characters/char_1")
    assert resp.status_code == 204
    resp = seeded_client.get("/api/characters")
    assert len(resp.json()) == 1


def test_character_zodiac_auto(client):
    resp = client.post("/api/characters", json={
        "id": "c1", "name": "A", "personality_code": "outgoing_dynamo",
        "birthday": "07-28",
    })
    assert resp.json()["zodiac"] == "사자자리"


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

def test_relationships_empty(client):
    resp = client.get("/api/relationships")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_relationship(seeded_client):
    resp = seeded_client.get("/api/relationships/char_1/char_2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stage"] == "stranger"
    assert data["status_text"] == "모르는 사이"


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

def test_memory_empty(seeded_client):
    resp = seeded_client.get("/api/memory/char_1")
    assert resp.status_code == 200
    assert resp.json() == []

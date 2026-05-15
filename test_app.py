import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import sqlite3

from app import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_check_returns_id():
    response = client.post("/api/v1/checks", json={"name": "test-check"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], str)
    assert len(data["id"]) > 0

def test_ping_updates_last_ping_at():
    # First create a check
    create_response = client.post("/api/v1/checks", json={"name": "test-check"})
    check_id = create_response.json()["id"]
    
    # Then ping it
    response = client.post(f"/ping/{check_id}")
    assert response.status_code == 200
    
    # Verify the check's last_ping_at was updated
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_ping_at FROM checks WHERE id = ?', (check_id,))
    result = cursor.fetchone()
    conn.close()
    
    assert result[0] is not None

def test_ping_unknown_id_returns_404():
    response = client.post("/ping/unknown-id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Check not found"}
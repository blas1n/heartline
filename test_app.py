import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import sqlite3
import os
from unittest.mock import patch, AsyncMock

from app import app

client = TestClient(app)

def setup_db():
    """Set up a clean database for testing."""
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM checks')  # Clear existing checks
    conn.commit()
    conn.close()

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_check_returns_id():
    setup_db()  # Clean database before test
    response = client.post("/api/v1/checks", json={"name": "test-check"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], str)
    assert len(data["id"]) > 0

def test_ping_check():
    setup_db()
    # Create a check first
    create_response = client.post("/api/v1/checks", json={"name": "test-check"})
    check_id = create_response.json()["id"]
    
    # Ping the check
    response = client.post(f"/ping/{check_id}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_checks_empty():
    setup_db()
    response = client.get("/api/v1/checks")
    assert response.status_code == 200
    assert response.json() == []

def test_list_checks_with_data():
    setup_db()
    
    # Create two checks
    response1 = client.post("/api/v1/checks", json={"name": "check1", "grace_seconds": 300})
    response2 = client.post("/api/v1/checks", json={"name": "check2", "grace_seconds": 600})
    
    check1_id = response1.json()["id"]
    check2_id = response2.json()["id"]
    
    # Ping the first check
    client.post(f"/ping/{check1_id}")
    
    response = client.get("/api/v1/checks")
    assert response.status_code == 200
    checks = response.json()
    
    assert len(checks) == 2
    
    # Find the checks in the response
    check1 = next((c for c in checks if c["id"] == check1_id), None)
    check2 = next((c for c in checks if c["id"] == check2_id), None)
    
    assert check1 is not None
    assert check2 is not None
    
    assert check1["name"] == "check1"
    assert check1["grace_seconds"] == 300
    assert check1["status"] == "ok"
    
    assert check2["name"] == "check2"
    assert check2["grace_seconds"] == 600
    assert check2["status"] == "pending"

def test_list_checks_status_classification():
    setup_db()
    
    # Create a check with a short grace period
    response = client.post("/api/v1/checks", json={"name": "test-check", "grace_seconds": 1})
    check_id = response.json()["id"]
    
    # Ping the check
    client.post(f"/ping/{check_id}")
    
    # Check status is 'ok'
    response = client.get("/api/v1/checks")
    checks = response.json()
    check = checks[0]
    assert check["status"] == "ok"
    
    # Simulate that the check is overdue by manually updating the database
    # (This would normally happen after grace_seconds have passed)
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    # Set last_ping_at to a time in the past (more than 1 second ago)
    past_time = (datetime.now() - timedelta(seconds=2)).isoformat()
    cursor.execute('UPDATE checks SET last_ping_at = ? WHERE id = ?', (past_time, check_id))
    conn.commit()
    conn.close()
    
    # Check status is 'overdue'
    response = client.get("/api/v1/checks")
    checks = response.json()
    check = checks[0]
    assert check["status"] == "overdue"

def test_status_endpoint_returns_200():
    setup_db()
    response = client.get("/status")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"

def test_status_endpoint_returns_html_with_checks():
    setup_db()
    
    # Create a check
    response = client.post("/api/v1/checks", json={"name": "test-check"})
    check_id = response.json()["id"]
    
    # Ping the check
    client.post(f"/ping/{check_id}")
    
    response = client.get("/status")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "test-check" in response.text
    assert "green" in response.text  # Check should be green since it was pinged recently

def test_status_endpoint_with_overdue_check():
    setup_db()
    
    # Create a check with a short grace period
    response = client.post("/api/v1/checks", json={"name": "overdue-check", "grace_seconds": 1})
    check_id = response.json()["id"]
    
    # Don't ping the check - it should be pending or overdue
    
    response = client.get("/status")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "overdue-check" in response.text
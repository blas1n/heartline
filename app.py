from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid
import sqlite3
from typing import Optional
import os
import logging
import httpx

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            grace_seconds INTEGER DEFAULT 300,
            last_ping_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Pydantic models
class CheckCreate(BaseModel):
    name: str
    grace_seconds: Optional[int] = 300

class CheckResponse(BaseModel):
    id: str

class Check(BaseModel):
    id: str
    name: str
    grace_seconds: int
    last_ping_at: Optional[datetime]

# Alert functions
async def send_discord_alert(check_name: str):
    """Send alert via Discord webhook if configured."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.info(f"Discord webhook not configured, logging only for check '{check_name}'")
        return
    
    try:
        payload = {"content": f"Heartline: {check_name} missed its ping"}
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code != 204:
                logger.warning(f"Failed to send Discord alert: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending Discord alert: {e}")

async def tick_alerts():
    """Check all checks and send alerts for stale ones."""
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    
    # Get all checks
    cursor.execute('SELECT id, name, grace_seconds, last_ping_at FROM checks')
    checks = cursor.fetchall()
    conn.close()
    
    alert_count = 0
    
    for check_id, name, grace_seconds, last_ping_at in checks:
        # Check if check has never been pinged or if last ping is older than grace period
        now = datetime.now()
        if last_ping_at is None:
            # Check never pinged - use grace period from registration
            # For a check that's never been pinged, we consider it stale if it's been longer than grace period since creation
            # But we don't want to immediately alert newly created checks, so we'll set a reasonable default
            # In this case, we'll treat it as if it was pinged at the time of creation
            last_ping_time = now
        else:
            last_ping_time = datetime.fromisoformat(last_ping_at)
        
        grace_period = timedelta(seconds=grace_seconds)
        
        # If last ping is older than grace period, send alert
        if now - last_ping_time > grace_period:
            logger.info(f"Sending alert for stale check '{name}'")
            await send_discord_alert(name)
            alert_count += 1
    
    return alert_count

# Routes
@app.post("/api/v1/checks", response_model=CheckResponse)
def create_check(check: CheckCreate):
    check_id = str(uuid.uuid4())
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO checks (id, name, grace_seconds)
        VALUES (?, ?, ?)
    ''', (check_id, check.name, check.grace_seconds))
    conn.commit()
    conn.close()
    return CheckResponse(id=check_id)

@app.post("/ping/{check_id}")
def ping_check(check_id: str):
    conn = sqlite3.connect('heartline.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE checks
        SET last_ping_at = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), check_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="Check not found")
    
    return {"status": "ok"}

@app.post("/api/v1/admin/run-alerts")
async def run_alerts():
    """Admin endpoint to manually trigger alert checking."""
    count = await tick_alerts()
    return {"alerts_fired": count}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
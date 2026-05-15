from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid
import sqlite3
from typing import Optional

app = FastAPI()

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

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
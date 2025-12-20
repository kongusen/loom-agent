"""
Loom Studio Server
FastAPI 后端，提供 Trace 存储和查询 API
"""

import os
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from loom.studio.db import TraceDB

app = FastAPI(title="Loom Studio")
db = TraceDB("loom_traces.db")

# 静态文件（前端）
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# ============================================================================
# API Models
# ============================================================================

class TraceCreate(BaseModel):
    name: str

class EventCreate(BaseModel):
    trace_id: str
    event: Dict[str, Any]

# ============================================================================
# Routes
# ============================================================================

@app.get("/api/traces")
async def list_traces(limit: int = 50):
    return db.get_traces(limit)

@app.post("/api/traces")
async def create_trace(trace: TraceCreate):
    trace_id = db.create_trace(trace.name)
    return {"id": trace_id}

@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    trace = db.get_trace_details(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace

@app.post("/api/events")
async def add_event(event_data: EventCreate):
    db.add_event(event_data.trace_id, event_data.event)
    return {"status": "ok"}

# ============================================================================
# Frontend Serving
# ============================================================================

@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "Loom Studio Frontend - index.html not found"

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

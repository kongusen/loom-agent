
import asyncio
import uuid
import json
from typing import Set, Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, Query
from fastapi.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="Loom Studio Server")

# Allow CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-Memory Store ---
# In a real impl, this would wrap database access
class SimpleEventStore:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._seen_ids: Set[str] = set()  # 用于去重

    async def append(self, event: Dict[str, Any]):
        # 基于 event.id 去重（同一个事件不应该被存储两次）
        event_id = event.get("id")
        if event_id and event_id in self._seen_ids:
            # 如果事件已存在，跳过（避免重复）
            return
        
        if event_id:
            self._seen_ids.add(event_id)
        
        self.events.append(event)
        # Keep basic size limit
        if len(self.events) > 10000:
            removed = self.events.pop(0)
            # 清理已移除事件的 ID
            if removed.get("id"):
                self._seen_ids.discard(removed.get("id"))

    async def get_events(self, limit: int = 100, offset: int = 0, **filters) -> List[Dict[str, Any]]:
        # Apply filters (basic implementation)
        filtered = self.events
        
        # Filter by source (node_id)
        if "source__contains" in filters:
            node_id = filters["source__contains"]
            filtered = [e for e in filtered if node_id in e.get("source", "")]
            
        # Filter by type
        if "type" in filters:
            etype = filters["type"]
            filtered = [e for e in filtered if e.get("type") == etype]

        # Filter by type list
        if "type__in" in filters:
            types = filters["type__in"]
            filtered = [e for e in filtered if e.get("type") in types]
            
        # Reverse to get newest first, then apply limit/offset
        # Actually usually frontend wants chronological or reverse chronological?
        # Let's return reverse chronological (newest first) for initial load
        # But for streaming it's chronological.
        # Let's do slicing on the original list (chronological) 
        # but apply offset from end if needed? 
        # Standard: return slice
        res = filtered[offset : offset + limit]
        return res

event_store = SimpleEventStore()

# --- Connection Manager ---

class ConnectionManager:
    """Manages WebSocket connections"""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast event to all connected frontends"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        self.active_connections -= disconnected

manager = ConnectionManager()

# --- WebSocket Endpoints ---

@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """Frontend connection: receive real-time events"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

@app.websocket("/ws/ingest")
async def ingest_endpoint(websocket: WebSocket):
    """Framework connection: receive events from StudioInterceptor"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "event_batch":
                # Process batch
                events = data.get("events", [])
                for event in events:
                    # Store
                    await event_store.append(event)

                    # Broadcast event
                    await manager.broadcast({
                        "type": "event",
                        "data": event
                    })
                
                # After processing events, broadcast topology update via WebSocket
                topology = _compute_topology()
                await manager.broadcast({
                    "type": "topology",
                    "data": topology
                })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Error in ingest: {e}")


# --- REST API Endpoints ---

@app.get("/api/events")
async def get_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    node_id: Optional[str] = None,
    event_type: Optional[str] = None
):
    """Query history events"""
    filters = {}
    if node_id:
        filters["source__contains"] = node_id
    if event_type:
        filters["type"] = event_type

    events = await event_store.get_events(limit=limit, offset=offset, **filters)
    return {"events": events, "total": len(events)} # Total is rough approx

def _infer_node_type(event: Dict[str, Any]) -> str:
    """Simple heuristic to infer node type from event"""
    source = event.get("source", "")
    if not source:
        return "Node"
    
    # 规范化 source（移除开头的 /）
    normalized = source.lstrip('/')
    
    # 检查路径中是否包含类型标识
    if "/agent/" in normalized or normalized.startswith("agent/"):
        return "AgentNode"
    if "/tool/" in normalized or normalized.startswith("tool/"):
        return "ToolNode"
    if "/crew/" in normalized or normalized.startswith("crew/"):
        return "CrewNode"
    
    # 也检查 node/agent, node/tool, node/crew 格式
    if "node/agent" in normalized:
        return "AgentNode"
    if "node/tool" in normalized:
        return "ToolNode"
    if "node/crew" in normalized:
        return "CrewNode"

    return "Node"

def _compute_topology():
    """Compute topology from events (extracted as function for reuse)"""
    events = event_store.events # Get all for topology
    
    nodes = {}
    edges = {}

    for event in events:
        source = event.get("source")
        subject = event.get("subject")

        # Record Node
        if source and source not in nodes:
            nodes[source] = {
                "id": source,
                "type": _infer_node_type(event),
                "metadata": {}
            }
        
        # Also maybe the subject is a node (e.g. invalid target?)
        # But usually subject is just a string target ID.
        if subject and subject not in nodes:
             # Heuristic: if subject looks like a path, infer type
             nodes[subject] = {
                 "id": subject,
                 "type": _infer_node_type({"source": subject}),  # 使用相同的推断逻辑
                 "metadata": {}
             }

        # Record Edge
        if source and subject:
            edge_key = f"{source}->{subject}"
            edges[edge_key] = edges.get(edge_key, 0) + 1

    return {
        "nodes": list(nodes.values()),
        "edges": [
            {"from": k.split("->")[0], "to": k.split("->")[1], "count": v}
            for k, v in edges.items()
        ]
    }

@app.get("/api/topology")
async def get_topology():
    """Get node topology inferred from events"""
    return _compute_topology()

@app.get("/api/memory/{node_id:path}")
async def get_memory(node_id: str):
    """Get memory state for a node"""
    # Find events related to memory
    # Note: node_id might contain slashes, so use path param
    
    events = await event_store.get_events(
        limit=1000, 
        source__contains=node_id, 
        type__in=["memory.add", "memory.consolidate", "agent.thought"]
    )
    
    # In a real system, we would query the Agent's actual memory state via a control plane command
    # Or rely on the agent strictly emitting all memory changes as events.
    # For now, just return the events as a log of memory.
    
    return {"node_id": node_id, "memory": events}

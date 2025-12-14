"""
FastAPI Integration with Streaming - loom-agent v0.1.1

Demonstrates:
- REST API integration
- Server-Sent Events (SSE) streaming
- Session management
- Crash recovery
- Production-ready patterns

Usage:
    pip install fastapi uvicorn sse-starlette
    python fastapi_integration.py

    # Test endpoints:
    curl -X POST http://localhost:8000/agent/chat -H "Content-Type: application/json" -d '{"message": "Hello"}'
    curl -X POST http://localhost:8000/agent/chat/stream -H "Content-Type: application/json" -d '{"message": "Hello"}'
"""

import asyncio
from typing import Dict, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from loom import agent
from loom.builtin.tools import ReadFileTool, WriteFileTool, BashTool
from loom.core.lifecycle_hooks import HITLHook
from loom.core.events import AgentEventType


# ===== Request/Response Models =====

class ChatRequest(BaseModel):
    """Chat request payload"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response payload"""
    response: str
    session_id: str
    timestamp: str


class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    created_at: str
    message_count: int
    last_activity: str


# ===== FastAPI Application =====

app = FastAPI(
    title="Loom Agent API",
    description="Production-ready agent API with streaming support",
    version="0.1.6"
)


# Global agent instance (could be per-session in production)
# In production, use a session manager with Redis/database
_agent_instances: Dict[str, any] = {}


def get_or_create_agent(session_id: str = "default"):
    """Get or create agent for session."""
    if session_id not in _agent_instances:
        # Create HITL hook for dangerous tools
        hitl_hook = HITLHook(
            dangerous_tools=["bash", "write_file"],
            # In production, integrate with approval queue
            ask_user_callback=lambda msg: False  # Auto-deny for API
        )

        # Create agent with persistence
        _agent_instances[session_id] = agent(
            provider="openai",
            model="gpt-4",
            system_instructions="You are a helpful AI assistant with tool access.",
            tools=[
                ReadFileTool(),
                WriteFileTool(),
                BashTool()
            ],
            hooks=[hitl_hook],
            enable_persistence=True,
            journal_path=Path(f"./logs/{session_id}"),
            thread_id=session_id,
            max_iterations=20
        )

    return _agent_instances[session_id]


# ===== Endpoints =====

@app.get("/")
async def root():
    """API info"""
    return {
        "service": "Loom Agent API",
        "version": "0.1.1",
        "endpoints": {
            "chat": "/agent/chat (POST)",
            "chat_stream": "/agent/chat/stream (POST)",
            "session": "/agent/session/{session_id} (GET)",
            "resume": "/agent/resume/{session_id} (POST)"
        }
    }


@app.post("/agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint (simple mode).

    Returns final response only.
    """
    session_id = request.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    my_agent = get_or_create_agent(session_id)

    try:
        # Execute and wait for final result
        result = await my_agent.run(request.message)

        return ChatResponse(
            response=result,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Client receives real-time events:
    - delta: LLM response chunks
    - tool_start: Tool execution started
    - tool_result: Tool execution result
    - done: Final response
    """
    session_id = request.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    my_agent = get_or_create_agent(session_id)

    async def event_generator() -> AsyncGenerator[Dict, None]:
        """Generate SSE events from agent execution."""
        try:
            async for event in my_agent.execute(request.message):
                # Convert AgentEvent to SSE format

                if event.type == AgentEventType.LLM_DELTA:
                    # Stream text chunks
                    yield {
                        "event": "delta",
                        "data": {
                            "content": event.content,
                            "timestamp": event.timestamp
                        }
                    }

                elif event.type == AgentEventType.TOOL_EXECUTION_START:
                    # Tool execution started
                    yield {
                        "event": "tool_start",
                        "data": {
                            "tool_name": event.metadata.get('tool_name'),
                            "timestamp": event.timestamp
                        }
                    }

                elif event.type == AgentEventType.TOOL_RESULT:
                    # Tool execution completed
                    yield {
                        "event": "tool_result",
                        "data": {
                            "tool_name": event.tool_result.tool_name if event.tool_result else None,
                            "success": not (event.tool_result.is_error if event.tool_result else True),
                            "timestamp": event.timestamp
                        }
                    }

                elif event.type == AgentEventType.ITERATION_START:
                    # Iteration started
                    yield {
                        "event": "iteration",
                        "data": {
                            "iteration": event.metadata.get('iteration'),
                            "timestamp": event.timestamp
                        }
                    }

                elif event.type == AgentEventType.AGENT_FINISH:
                    # Final response
                    yield {
                        "event": "done",
                        "data": {
                            "final_result": event.content,
                            "session_id": session_id,
                            "timestamp": event.timestamp
                        }
                    }

                elif event.type == AgentEventType.ERROR:
                    # Error occurred
                    yield {
                        "event": "error",
                        "data": {
                            "error": str(event.error),
                            "timestamp": event.timestamp
                        }
                    }

        except Exception as e:
            yield {
                "event": "error",
                "data": {"error": str(e)}
            }

    return EventSourceResponse(event_generator())


@app.get("/agent/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get session information."""
    if session_id not in _agent_instances:
        raise HTTPException(status_code=404, detail="Session not found")

    # In production, fetch from database
    return SessionInfo(
        session_id=session_id,
        created_at=datetime.now().isoformat(),
        message_count=0,
        last_activity=datetime.now().isoformat()
    )


@app.post("/agent/resume/{session_id}")
async def resume_session(session_id: str):
    """
    Resume crashed or interrupted session.

    Uses EventJournal to replay from last checkpoint.
    """
    # Load agent with same thread_id
    my_agent = get_or_create_agent(session_id)

    try:
        # Resume execution from journal
        final_result = None

        async for event in my_agent.executor.resume(thread_id=session_id):
            if event.type == AgentEventType.AGENT_FINISH:
                final_result = event.content

        return {
            "status": "resumed",
            "session_id": session_id,
            "result": final_result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)}")


@app.delete("/agent/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session and cleanup resources."""
    if session_id in _agent_instances:
        del _agent_instances[session_id]
        return {"status": "deleted", "session_id": session_id}

    raise HTTPException(status_code=404, detail="Session not found")


# ===== Run Server =====

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Loom Agent API server...")
    print("📖 API docs: http://localhost:8000/docs")
    print("🔗 Test streaming: http://localhost:8000/agent/chat/stream")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

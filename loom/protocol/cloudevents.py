"""
CloudEvents v1.0 Implementation for Loom
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

class EventType:
    """Standard Event Types for Loom Cognitive Kernel."""
    
    # Standard Request/Response
    NODE_CALL = "node.call"
    NODE_RESULT = "node.result"
    NODE_ERROR = "node.error"
    
    # Cognitive Streams (System 1 & 2)
    STREAM_CHUNK = "agent.stream.chunk"   # System 1: Speech Stream
    THOUGHT_SPARK = "agent.thought.spark" # System 2: Crystallized Insight
    
    # Kernel Management
    NODE_REGISTER = "kernel.node.register"
    NODE_UNREGISTER = "kernel.node.unregister"


class CloudEvent(BaseModel):
    """
    CloudEvents 1.0 Specification Implementation.
    
    Attributes:
        specversion: The version of the CloudEvents specification which the event uses.
        id: Identifies the event.
        source: Identifies the context in which an event happened.
        type: Describes the type of event related to the originating occurrence.
        datacontenttype: Content type of data value.
        dataschema: Identifies the schema that data adheres to.
        subject: Describes the subject of the event in the context of the event producer (identified by source).
        time: Timestamp of when the occurrence happened.
        data: The event payload.
        traceparent: W3C Trace Context (Extension)
    """
    
    # Required Attributes
    specversion: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    type: str # e.g., "node.call", "agent.thought"
    
    # Optional Attributes
    datacontenttype: Optional[str] = "application/json"
    dataschema: Optional[str] = None
    subject: Optional[str] = None
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[Any] = None
    
    # Extensions
    traceparent: Optional[str] = None
    extensions: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        extra='allow'
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard CloudEvents dictionary structure."""
        return self.model_dump(exclude_none=True, by_alias=True)
    
    @classmethod
    def create(
        cls, 
        source: str, 
        type: str, 
        data: Optional[Any] = None, 
        subject: Optional[str] = None,
        traceparent: Optional[str] = None
    ) -> "CloudEvent":
        """Factory method to create a CloudEvent."""
        return cls(
            source=source,
            type=type,
            data=data,
            subject=subject,
            traceparent=traceparent
        )

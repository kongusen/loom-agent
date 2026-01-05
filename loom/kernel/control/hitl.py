"""
Human-in-the-Loop Interceptor
"""

import asyncio
from typing import List, Optional, Any
from loom.kernel.control.base import Interceptor
from loom.protocol.cloudevents import CloudEvent

class HITLInterceptor(Interceptor):
    """
    Pauses execution for Human Approval on sensitive events.
    """
    
    def __init__(self, patterns: List[str]):
        """
        Args:
            patterns: List of substring matches for Event Type or Subject.
                      e.g. ["tool.execute/delete_file", "payment"]
        """
        self.patterns = patterns

    async def pre_invoke(self, event: CloudEvent) -> Optional[CloudEvent]:
        # Check simple pattern match
        identifier = f"{event.type}/{event.subject or ''}"
        
        should_pause = any(p in identifier for p in self.patterns)
        
        if should_pause:
            print(f"\n[HITL] ⚠️  STOP! Event requires approval: {identifier}")
            print(f"       Data: {str(event.data)[:200]}")
            
            # This blocks the Dispatcher! 
            # In a real async web app, this would suspend and wait for an API call (Webhook/Signal).
            # For this CLI SDK, we use blocking input (in a separate thread if needed, or just sync).
            # Since standard input() is blocking, it pauses the loop. 
            # In purely async heavily concurrent apps, use a non-blocking wrapper.
            # Here: simplistic CLI approach.
            
            approval = await asyncio.to_thread(input, "       Approve? (y/N): ")
            
            if approval.lower().strip() != "y":
                print("       ❌ Denied.")
                return None # Drop event
            
            print("       ✅ Approved.")
            
        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        pass

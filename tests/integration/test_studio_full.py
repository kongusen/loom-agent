
import asyncio
import os
import pytest
from loom.protocol.cloudevents import CloudEvent
from loom.kernel.interceptors.studio import StudioInterceptor

@pytest.mark.asyncio
async def test_studio_interceptor_connectivity():
    # Ensure env var is set (though we pass enabled=True implicitly via code in main, 
    # but here we test the unit directly)
    os.environ["LOOM_STUDIO_ENABLED"] = "true"
    
    interceptor = StudioInterceptor(studio_url="ws://localhost:8765")
    
    # Wait a bit for connection
    await asyncio.sleep(1)
    
    event = CloudEvent.create(
        source="/test/source",
        type="test.event",
        data={"message": "Hello Studio"}
    )
    
    # Pre invoke
    await interceptor.pre_invoke(event)
    
    # Post invoke
    await interceptor.post_invoke(event)
    
    # Flush manually if needed, but it auto flushes on size. 
    # Let's force flush by sending enough events or just waiting/mocking
    # Actually interceptor logic: sends if buffer >= 10.
    
    for i in range(10):
        await interceptor.pre_invoke(event)
        
    # Allow some time for async tasks to run
    await asyncio.sleep(2)
    
    # We can't easily assert the server received it without querying the server API.
    # So let's query the server API using httpx or simpler, just regular requests.
    
    import urllib.request
    import urllib.error
    import json
    
    try:
        req = urllib.request.Request("http://localhost:8765/api/events")
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read().decode())
            print(f"Events found: {len(data['events'])}")
            assert len(data['events']) > 0
    except urllib.error.URLError as e:
        pytest.fail(f"Failed to connect to Studio Server: {e}. Make sure studio-backend is running.")
        
    print("Test Passed: Events successfully sent to and retrieved from Studio Server")

if __name__ == "__main__":
    asyncio.run(test_studio_interceptor_connectivity())

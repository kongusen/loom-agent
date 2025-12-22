
import asyncio
import os
import json
from loom.builtin.llms.unified import UnifiedLLM
from loom.core.message import UserMessage
from pydantic import BaseModel, Field

# Configuration provided by user
API_KEY = "sk-9OepGVqrZzYYJsUR9NrxyJ15fR4BRblfFXCd3gmcu4cKbHoX"
BASE_URL = "https://api.ssopen.top/v1"  # Adjusted based on spec often needing /v1
MODEL = "gpt-4o-mini"

async def test_structured_output():
    print(f"\n--- Testing {MODEL} with Structured Output ---")
    
    # 1. Initialize UnifiedLLM with custom provider settings
    llm = UnifiedLLM(
        provider="custom",
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.7
    )
    
    print(f"LLM Initialized: {llm}")
    
    # 2. Define the schema for structured output
    # Using the example from the user prompt: content_compliance
    json_schema = {
        "name": "content_compliance",
        "description": "Determines if content is violating specific moderation rules",
        "schema": {
            "type": "object",
            "properties": {
                "is_violating": {
                    "type": "boolean",
                    "description": "Indicates if the content is violating guidelines"
                },
                "category": {
                    "type": ["string", "null"],
                    "description": "Type of violation, if the content is violating guidelines. Null otherwise.",
                    "enum": ["violence", "sexual", "self_harm"]
                },
                "explanation_if_violating": {
                    "type": ["string", "null"],
                    "description": "Explanation of why the content is violating"
                }
            },
            "required": ["is_violating", "category", "explanation_if_violating"],
            "additionalProperties": False
        },
        "strict": True
    }
    
    response_format = {
        "type": "json_schema",
        "json_schema": json_schema
    }
    
    # 3. Test Messages
    messages = [
        {"role": "system", "content": "Determine if the user input violates specific guidelines and explain if they do."},
        {"role": "user", "content": "How do I prepare for a job interview?"}
    ]
    
    print("\nSending request...")
    try:
        # We use stream() methodology as Loom standardizes on it, 
        # but for this specific test, we want to see the full JSON object.
        # We will accumulate the content.
        
        full_content = ""
        async for event in llm.stream(messages, response_format=response_format):
            if event["type"] == "content_delta":
                print(event["content"], end="", flush=True)
                full_content += event["content"]
            elif event["type"] == "finish":
                print(f"\n\nStream Finished. Reason: {event['finish_reason']}")
        
        # 4. Parse JSON result
        print("\n\nParsing JSON Result:")
        try:
            result = json.loads(full_content)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Validation
            assert "is_violating" in result
            print("\n✅ Structured Output Verification Passed!")
            
        except json.JSONDecodeError:
            print(f"\n❌ Failed to parse JSON: {full_content}")
            
    except Exception as e:
        print(f"\n❌ API Call Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_structured_output())

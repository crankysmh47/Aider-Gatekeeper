"""FastAPI application for Aider-Gatekeeper proxy."""
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from aider_gatekeeper.chetna_ai import process_chetna_ai_integration
from aider_gatekeeper.token_truncation import truncate_payload
from aider_gatekeeper.yaml_injection import inject_yaml_into_system_prompt

app = FastAPI(title="Aider-Gatekeeper", version="0.1.0")

# Target LLM server (llama.cpp)
LLM_BASE_URL = "http://localhost:8080"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> StreamingResponse:
    """
    Intercept OpenAI-compatible chat completion requests from Aider.

    Pipeline:
    1. Receive payload from Aider
    2. Phase 3: Inject YAML rules from project_context.yaml
    3. Phase 5: Query ChetnaAI and inject episodic memory
    4. Phase 4: Truncate payload if token limit exceeded
    5. Forward to llama.cpp and stream response back
    """
    payload: dict[str, Any] = await request.json()
    messages: list[dict[str, Any]] = payload.get("messages", [])

    print(f"[Gatekeeper] Received payload with {len(messages)} messages")

    # Phase 3: YAML Rule Injection
    messages = inject_yaml_into_system_prompt(messages)
    print(f"[Gatekeeper] Phase 3: YAML injection complete, {len(messages)} messages")

    # Phase 5: ChetnaAI Sidecar Integration
    messages = await process_chetna_ai_integration(messages)
    print(f"[Gatekeeper] Phase 5: ChetnaAI integration complete, {len(messages)} messages")

    # Phase 4: Token-Accurate Truncation
    messages = truncate_payload(messages, max_tokens=9500)
    print(f"[Gatekeeper] Phase 4: Token truncation complete, {len(messages)} messages")

    # Update payload with processed messages
    payload["messages"] = messages

    # Forward to llama.cpp and stream response back
    async def generate() -> AsyncGenerator[bytes, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{LLM_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=None,
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

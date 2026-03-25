"""FastAPI application for Aider-Gatekeeper proxy."""
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from aider_gatekeeper.chetna_ai import process_chetna_ai_integration
from aider_gatekeeper.token_truncation import truncate_payload
from aider_gatekeeper.yaml_injection import inject_yaml_into_system_prompt

# LLM engine URLs
_OLLAMA_URL = "http://localhost:11434"
_LLAMACPP_URL = "http://localhost:8080"

# Resolved at startup by the lifespan handler; defaults to Ollama.
LLM_BASE_URL: str = _OLLAMA_URL


async def _resolve_llm_url() -> str:
    """Ping Ollama; fall back to llama.cpp if unreachable.

    Returns:
        The base URL of whichever engine responded first.
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.head(_OLLAMA_URL, timeout=2.0)
        print(f"[Gatekeeper] LLM engine: Ollama ({_OLLAMA_URL})")
        return _OLLAMA_URL
    except (httpx.ConnectError, httpx.TimeoutException):
        print(
            f"[Gatekeeper] Ollama not reachable — falling back to llama.cpp ({_LLAMACPP_URL})"
        )
        return _LLAMACPP_URL


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Resolve the active LLM engine once at startup."""
    global LLM_BASE_URL
    LLM_BASE_URL = await _resolve_llm_url()
    yield


app = FastAPI(title="Aider-Gatekeeper", version="0.1.0", lifespan=lifespan)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> StreamingResponse:
    """
    Intercept OpenAI-compatible chat completion requests from Aider.

    Pipeline:
    1. Receive payload from Aider
    2. Phase 3: Inject YAML rules from project_context.yaml
    3. Phase 5: Query ChetnaAI and inject episodic memory
    4. Phase 4: Truncate payload if token limit exceeded
    5. Forward to active LLM engine and stream response back
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

    # Capture the resolved URL at request time (set during lifespan startup)
    target_url = f"{LLM_BASE_URL}/v1/chat/completions"

    async def generate() -> AsyncGenerator[bytes, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                target_url,
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

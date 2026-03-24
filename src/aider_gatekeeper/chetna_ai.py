"""ChetnaAI Sidecar Integration for Aider-Gatekeeper.

Uses the real Chetna memory API (https://github.com/vineetkishore01/Chetna).
Chetna runs on http://localhost:1987 by default.

Endpoints used:
  - GET  /api/memory/search?query=<text>&limit=<n>  -> list of Memory objects
  - GET  /health                                    -> "OK" health check
"""
from typing import Any

import httpx

# Real Chetna server URL (can be overridden via CHETNA_URL env var for flexibility)
CHETNA_BASE_URL = "http://localhost:1987"
CHETNA_SEARCH_URL = f"{CHETNA_BASE_URL}/api/memory/search"
CHETNA_HEALTH_URL = f"{CHETNA_BASE_URL}/health"

# How many memories to retrieve per query
CHETNA_RECALL_LIMIT = 5


def extract_latest_user_message(messages: list[dict[str, Any]]) -> str | None:
    """
    Extract the latest user message from the conversation.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.

    Returns:
        The content of the latest user message, or None if not found.
    """
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content")
    return None


def _format_memory_summary(memories: list[dict[str, Any]]) -> str | None:
    """
    Convert a list of Chetna Memory objects into a concise summary string.

    Chetna returns a list of objects with at minimum:
        { "id": "...", "content": "...", "importance": 0.9, ... }

    Returns:
        A newline-separated summary of memory contents, or None if empty.
    """
    if not memories:
        return None
    lines = []
    for m in memories:
        content = m.get("content", "").strip()
        if content:
            importance = m.get("importance", 0.0)
            lines.append(f"- [{importance:.1f}] {content}")
    if not lines:
        return None
    return "\n".join(lines)


async def query_chetna(user_message: str) -> str | None:
    """
    Query the real Chetna memory API for episodic memories relevant to the
    user's message.

    Uses GET /api/memory/search?query=<text>&limit=<n>

    Args:
        user_message: The user's query to search for relevant memories.

    Returns:
        A compact multi-line summary of relevant memories, or None on failure.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                CHETNA_SEARCH_URL,
                params={"query": user_message, "limit": CHETNA_RECALL_LIMIT},
                timeout=5.0,
            )
            if response.status_code == 200:
                memories: list[dict[str, Any]] = response.json()
                return _format_memory_summary(memories)
            return None
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        # Chetna is a sidecar — fail silently so Aider is never blocked
        return None


def inject_chetna_memory_into_payload(
    messages: list[dict[str, Any]],
    memory_summary: str | None,
) -> list[dict[str, Any]]:
    """
    Inject Chetna memory summary into the payload right after the system prompt.

    Args:
        messages: List of message dictionaries.
        memory_summary: The memory summary from Chetna, or None.

    Returns:
        Modified messages with memory injected after the first system message.
    """
    if not memory_summary or not messages:
        return messages

    for i, message in enumerate(messages):
        if message.get("role") == "system":
            memory_message = {
                "role": "system",
                "content": f"[Episodic Memory from Chetna]\n{memory_summary}",
            }
            messages.insert(i + 1, memory_message)
            break

    return messages


async def process_chetna_ai_integration(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Full pipeline: extract latest user message → query Chetna → inject memories.

    Args:
        messages: List of message dictionaries.

    Returns:
        Modified messages with Chetna episodic memory injected (if any found).
    """
    user_message = extract_latest_user_message(messages)
    if user_message:
        memory = await query_chetna(user_message)
        if memory:
            messages = inject_chetna_memory_into_payload(messages, memory)
    return messages

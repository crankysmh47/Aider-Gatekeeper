"""YAML Rule Injection utility for Aider-Gatekeeper."""
import os
from pathlib import Path
from typing import Any

import yaml


def load_project_context_yaml(cwd: str | Path | None = None) -> str | None:
    """
    Check for project_context.yaml in the current working directory.

    Args:
        cwd: The directory to look in. Defaults to current working directory.

    Returns:
        The contents of the YAML file as a string, or None if not found.
    """
    if cwd is None:
        cwd = os.getcwd()

    yaml_path = Path(cwd) / "project_context.yaml"

    if not yaml_path.exists():
        return None

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError):
        return None


def inject_yaml_into_system_prompt(
    messages: list[dict[str, Any]],
    cwd: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Inject project_context.yaml contents into the first system message.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.

    Returns:
        Modified messages list with YAML content injected into the first system prompt.
    """
    if not messages:
        return messages

    yaml_content = load_project_context_yaml(cwd)

    if yaml_content is None:
        return messages

    # Find the first system message
    for message in messages:
        if message.get("role") == "system":
            original_content = message.get("content", "")
            # Prepend YAML content to the system prompt
            message["content"] = f"[Project Context]\n{yaml_content}\n\n{original_content}"
            break

    return messages

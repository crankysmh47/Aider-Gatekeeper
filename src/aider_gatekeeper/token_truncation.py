"""Token truncation utility for Aider-Gatekeeper.

Uses HuggingFace AutoTokenizer for Qwen 3.5 9B to accurately count tokens
and truncate conversation history while preserving critical messages.
"""
from typing import Any

from transformers import AutoTokenizer

from aider_gatekeeper.config import settings


class TokenCounter:
    """Tokenizer wrapper for counting tokens in messages."""

    def __init__(self, model_name: str = settings.default_model) -> None:
        """Initialize the tokenizer.

        Args:
            model_name: HuggingFace model identifier for the tokenizer.
        """
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        except Exception:
            # Fallback to a generic tokenizer if model not available
            self.tokenizer = AutoTokenizer.from_pretrained("gpt2")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: The text to tokenize.

        Returns:
            Number of tokens.
        """
        if not text:
            return 0
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        return len(tokens)

    def count_message_tokens(self, message: dict[str, Any]) -> int:
        """Count tokens in a single message.

        Args:
            message: A message dict with 'role' and 'content' keys.

        Returns:
            Number of tokens in the message.
        """
        role = message.get("role", "")
        content = message.get("content", "")
        # Format: "role: content" plus some overhead for message formatting
        formatted = f"{role}: {content}"
        return self.count_tokens(formatted)

    def count_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count total tokens in a list of messages.

        Args:
            messages: List of message dictionaries.

        Returns:
            Total token count.
        """
        total = 0
        for msg in messages:
            total += self.count_message_tokens(msg)
        return total


# Global tokenizer instance
_tokenizer: TokenCounter | None = None


def get_tokenizer() -> TokenCounter:
    """Get or create the global tokenizer instance."""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = TokenCounter()
    return _tokenizer


def truncate_payload(
    messages: list[dict[str, Any]],
    max_tokens: int = settings.max_tokens,
) -> list[dict[str, Any]]:
    """
    Truncate conversation history to fit within token limit.

    The truncation strategy preserves:
    1. All consecutive leading system messages (e.g. main system prompt +
       any injected episodic-memory system messages) - always kept
    2. The last 4 messages (recent conversation) - always kept
    3. Removes middle messages if token limit exceeded

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.
        max_tokens: Maximum allowed tokens (default: 9500).

    Returns:
        Truncated list of messages that fits within token limit.
    """
    if not messages:
        return messages

    # Dynamically protect all consecutive leading system messages.
    # This covers the main system prompt (index 0) as well as any
    # injected system messages immediately following it (e.g. ChetnaAI
    # episodic memory at index 1).
    num_leading = 0
    for msg in messages:
        if msg.get("role") == "system":
            num_leading += 1
        else:
            break

    leading_messages = messages[:num_leading]
    last_messages = messages[-4:]

    # If the list is too short to have a meaningful middle, return as-is.
    if len(messages) <= num_leading + 4:
        return messages

    tokenizer = get_tokenizer()

    # Calculate tokens for the preserved bookends.
    leading_tokens = tokenizer.count_messages_tokens(leading_messages)
    last_tokens = tokenizer.count_messages_tokens(last_messages)
    total_preserved = leading_tokens + last_tokens

    # If preserved messages already exceed limit, return them anyway
    # (can't drop system prompts or latest user query per requirements).
    if total_preserved >= max_tokens:
        return leading_messages + last_messages

    # Calculate remaining budget for middle messages.
    remaining_budget = max_tokens - total_preserved

    # Middle = everything between the protected leading block and last 4.
    middle_messages = messages[num_leading:-4]

    # Select middle messages from the end (most recent context first).
    selected_middle: list[dict[str, Any]] = []
    current_tokens = 0

    for msg in reversed(middle_messages):
        msg_tokens = tokenizer.count_message_tokens(msg)
        if current_tokens + msg_tokens <= remaining_budget:
            selected_middle.insert(0, msg)  # maintain chronological order
            current_tokens += msg_tokens
        else:
            break

    # Return: all leading system messages + selected middle + last 4.
    return leading_messages + selected_middle + last_messages


def get_token_stats(messages: list[dict[str, Any]]) -> dict[str, int]:
    """Get token statistics for a list of messages.

    Args:
        messages: List of message dictionaries.

    Returns:
        Dict with token counts per message and total.
    """
    tokenizer = get_tokenizer()
    stats = {
        "total": tokenizer.count_messages_tokens(messages),
        "count": len(messages),
    }
    return stats

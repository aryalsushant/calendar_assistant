"""
Thin wrapper around the Google GenAI SDK (google.genai).
"""

from google import genai

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

# Create a single client instance
_client = genai.Client(api_key=GEMINI_API_KEY)


async def generate(
    prompt: str,
    system_instruction: str | None = None,
) -> str:
    """
    Send a prompt to Gemini and return the text response.

    Args:
        prompt: The user/system prompt.
        system_instruction: Optional system-level instruction.

    Returns:
        The model's text response.

    Raises:
        RuntimeError: If the API call fails.
    """
    try:
        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction

        response = await _client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}") from e

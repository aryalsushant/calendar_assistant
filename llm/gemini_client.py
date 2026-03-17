"""
Thin wrapper around the Google Generative AI (Gemini) SDK.
"""

import google.generativeai as genai

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

# Configure once at import time
genai.configure(api_key=GEMINI_API_KEY)


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
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_instruction,
        )
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}") from e

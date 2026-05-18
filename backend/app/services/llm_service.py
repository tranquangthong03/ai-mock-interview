"""
Shared LLM Service
Provides a single generate_text() function used by all services that need LLM.

Supported providers:
  - gemini  : Google Gemini API (requires GEMINI_API_KEY)
  - groq    : Groq API (requires GROQ_API_KEY)
  - ollama  : Ollama local (requires OLLAMA_BASE_URL)

Environment variables:
  LLM_PROVIDER  = "gemini" | "groq" | "ollama"  (default: "gemini")
  LLM_MODEL     = model name override (optional)
  GEMINI_API_KEY = API key for Google Gemini
  GROQ_API_KEY   = API key for Groq
  OLLAMA_BASE_URL = base URL for Ollama (default: http://localhost:11434)
"""

import os
from typing import Optional


# ---------------------------------------------------------------------------
# LLM Provider implementations
# ---------------------------------------------------------------------------

def _call_gemini(system_prompt: str, user_text: str, model: Optional[str] = None) -> str:
    """Call Google Gemini API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it before using the Gemini provider."
        )

    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai package is not installed. "
            "Run: pip install google-generativeai"
        )

    genai.configure(api_key=api_key)
    model_name = model or "gemini-2.0-flash"
    llm = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )

    response = llm.generate_content(user_text)
    return response.text


def _call_groq(system_prompt: str, user_text: str, model: Optional[str] = None) -> str:
    """Call Groq API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY environment variable is not set. "
            "Please set it before using the Groq provider."
        )

    try:
        from groq import Groq
    except ImportError:
        raise ImportError(
            "groq package is not installed. "
            "Run: pip install groq"
        )

    client = Groq(api_key=api_key)
    model_name = model or "llama-3.3-70b-versatile"

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    return response.choices[0].message.content


def _call_ollama(system_prompt: str, user_text: str, model: Optional[str] = None) -> str:
    """Call Ollama local API."""
    import requests

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = model or "llama3"

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model_name,
                "system": system_prompt,
                "prompt": user_text,
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {base_url}. "
            "Make sure Ollama is running locally."
        )

    return response.json()["response"]


# Provider registry
_PROVIDERS = {
    "gemini": _call_gemini,
    "groq": _call_groq,
    "ollama": _call_ollama,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_text(prompt: str, system_prompt: str = "") -> str:
    """
    Generate text using the configured LLM provider.

    Args:
        prompt: The user/main prompt text.
        system_prompt: Optional system instruction for the LLM.

    Returns:
        Raw text response from the LLM.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    model = os.getenv("LLM_MODEL") or None  # treat empty string as None

    if provider not in _PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. "
            f"Supported: {', '.join(_PROVIDERS.keys())}"
        )

    print(f"[LLM] Calling provider={provider}, model={model or 'default'}")
    return _PROVIDERS[provider](system_prompt, prompt, model)

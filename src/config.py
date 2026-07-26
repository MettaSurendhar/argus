"""
Central config for Argus. Owns:
- .env loading
- call_llm(prompt) -> str, branching on LLM_PROVIDER
- shared constants
"""
import os
from dotenv import load_dotenv

# resolve everything relative to this file's location, not whatever directory
# the caller happens to be running from — matters once another repo (the
# hackathon instrumentation one) starts importing this module directly
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ARGUS_ROOT = os.path.join(_THIS_DIR, "..")

load_dotenv(os.path.join(_ARGUS_ROOT, ".env"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# gpt-oss-120b replaced llama-3.3-70b-versatile after Groq's June 2026 deprecation.
# Swap to "openai/gpt-oss-20b" if you want higher free-tier rate limits over raw capability.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_ARGUS_ROOT, "chroma_db"))
TOOL_DATA_SOURCE = os.getenv("TOOL_DATA_SOURCE", "live")  # "live" | "snapshot"

# Shared constants (used by ingestion + retrieval — keep in sync)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"  # avoids CUDA compute-capability mismatches on older GPUs;
                          # embedding a handful of short runbook chunks doesn't need a GPU anyway
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
DEFAULT_TOP_K = 3


def call_llm(prompt: str) -> str:
    """
    Single entrypoint for LLM calls. Raises on failure — callers must not
    silently swallow errors, since a silently-empty answer is worse than
    a visible crash for an SRE tool.
    """
    if LLM_PROVIDER == "gemini":
        return _call_gemini(prompt)
    elif LLM_PROVIDER == "openrouter":
        return _call_openrouter(prompt)
    elif LLM_PROVIDER == "groq":
        return _call_groq(prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r} (expected 'gemini', 'openrouter', or 'groq')")


def _call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in .env")
    from openai import OpenAI

    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty response")
    return content


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    if not response.text:
        raise RuntimeError("Gemini returned an empty response")
    return response.text


def _call_openrouter(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenRouter returned an empty response")
    return content
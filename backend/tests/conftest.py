"""
Pytest-wide setup.

1. On Windows, psycopg's async driver requires the Selector event loop policy —
   the default Proactor policy raises 'Psycopg cannot use the ProactorEventLoop
   to run in async mode' the moment any test touches the database.

2. Compatibility stub for a ragas bug (upstream issue: explodinggradients/ragas#2753):
   ragas unconditionally imports langchain_community.chat_models.vertexai at
   startup, even for users who never touch Google Vertex AI. Recent
   langchain-community releases dropped that submodule entirely (moved to the
   separate langchain-google-vertexai package), so importing ragas crashes for
   every Groq/OpenAI/Anthropic user with a modern langchain-community install.
   We register a fake module at that import path before ragas ever loads, so
   the import succeeds. The stub is never actually instantiated — we don't use
   Vertex AI anywhere in this app.
"""
import asyncio
import sys
import types

from dotenv import load_dotenv
load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if "langchain_community.chat_models.vertexai" not in sys.modules:
    try:
        import langchain_community.chat_models.vertexai  # type: ignore[import-not-found]  # noqa: F401 — use the real one if it exists
    except ModuleNotFoundError:
        _stub = types.ModuleType("langchain_community.chat_models.vertexai")

        class ChatVertexAI:  # placeholder only — ragas imports this name but this app never calls it
            def __init__(self, *args, **kwargs):
                raise RuntimeError(
                    "ChatVertexAI is not available (compatibility stub). "
                    "This app does not use Google Vertex AI."
                )

        _stub.ChatVertexAI = ChatVertexAI  # type: ignore[attr-defined]
        sys.modules["langchain_community.chat_models.vertexai"] = _stub
import os
from pydantic import SecretStr
from langchain_groq import ChatGroq


def get_llm_model(temperature: float = 0.1):
    """Primary conversational/reasoning model — used for the main agent loop
    (multi-turn chat, tool orchestration, RAG synthesis). Higher quality, higher cost."""
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set in backend/.env. This app is configured to use Groq."
        )

    return ChatGroq(  # type: ignore[call-arg]
        api_key=SecretStr(groq_api_key),
        model=os.getenv("MODEL_NAME", "openai/gpt-oss-120b"),
        temperature=temperature,
        streaming=True,
    )


def get_classifier_model(temperature: float = 0.0):
    """Fast, cheap model dedicated to short deterministic decisions: the scope
    supervisor, memory-fact extraction, and document relevance/validation. Never
    streamed — these calls need one clean answer, not tokens trickling to the UI."""
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set in backend/.env. This app is configured to use Groq."
        )

    return ChatGroq(  # type: ignore[call-arg]
        api_key=SecretStr(groq_api_key),
        model=os.getenv("GROQ_CLASSIFIER_MODEL", "openai/gpt-oss-20b"),
        temperature=temperature,
        streaming=False,
    )
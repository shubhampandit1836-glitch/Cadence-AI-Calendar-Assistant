import os
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.config.llm_config import get_llm_model, get_classifier_model
from src.services.agent_tools_service import get_calendar_tools_for_user
from src.services.calendar_service import get_primary_calendar_timezone
from src.config.agent_instructions import get_agent_instructions
from src.config.db_pool import get_checkpointer
from src.repositories.thread_repository import (
    upsert_thread,
    touch_thread,
    list_threads,
    delete_thread_and_checkpoint,
)
from src.repositories.memory_repository import add_memory_fact, get_recent_facts

# The classifier model (openai/gpt-oss-20b by default) has an 8,000 token/minute cap on
# Groq's free tier. A single reply can easily be a huge tool-result table (e.g. a 60-day
# schedule listing) — sending that wholesale into a classifier prompt blows the cap and
# raises a 413. Truncate any text before it goes into a classifier-model prompt.
_CLASSIFIER_TEXT_LIMIT = 1500


def _truncate_for_classifier(text: str, limit: int = _CLASSIFIER_TEXT_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + " …(truncated)"


def _friendly_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "rate limit" in text or "429" in text or "quota" in text or "413" in text or "tokens per minute" in text:
        return "I'm getting a lot of requests right now. Please wait a few seconds and try again."
    if "timeout" in text or "timed out" in text:
        return "That took longer than expected. Please try again."
    if "connection" in text or "connect" in text or "network" in text:
        return "I'm having trouble connecting right now. Please try again in a moment."
    if "401" in text or "unauthor" in text or "invalid api key" in text or "403" in text:
        return "I'm having trouble accessing something I need right now. Please try again shortly."
    if "500" in text or "502" in text or "503" in text:
        return "The service is temporarily unavailable. Please try again in a moment."
    return "Something went wrong on my end. Please try again — if this keeps happening, let the developer know."


def _build_message_content(message: str, attachments: Optional[List[str]]) -> str:
    text = (message or "").strip()
    if not attachments:
        return text
    names = ", ".join(attachments)
    if text:
        return f"{text}\n\n[Attached: {names}]"
    return f"[Attached: {names}]"


_SUPERVISOR_PROMPT = """You are a strict intent classifier for a Google Calendar assistant.
Reply with exactly one word: IN_SCOPE or OUT_OF_SCOPE.

Recent conversation (for context only):
{context}

IN_SCOPE includes ALL of the following:
- Viewing, creating, rescheduling, canceling meetings, or checking availability
- Inquiring about, listing, or deleting uploaded work documents, agendas, meeting notes, sprint plans —
  including short follow-up questions about people, counts, dates, or details from a document already
  discussed earlier in this conversation (e.g. "how many Johns are there", "what's his email", "which one")
- Short replies that directly answer a question the assistant just asked (an email, a time, a name, yes/no)
- Simple greetings, small talk, thanks, or introducing/sharing the user's own name
- Questions about the assistant's own identity or capabilities ("what can you do", "who are you")
- Asking the assistant to recall something the user told it earlier in this conversation or in stored preferences

OUT_OF_SCOPE = general knowledge, news, sports, definitions of unrelated technical concepts, coding
help, or any other topic unrelated to this assistant and not covered above.

New message: {message}
Answer:"""

_OFF_TOPIC_REPLY = (
    "I'm your calendar assistant, so I can only help with scheduling — viewing, creating, "
    "rescheduling, or canceling meetings, and checking availability. Want help with any of those?"
)

_MEMORY_EXTRACT_PROMPT = """Read this exchange and decide if it reveals a durable, reusable fact
about the user for future scheduling conversations — their name, a recurring preference (meeting
length, time of day, working hours), or a frequently mentioned contact.

Do NOT extract facts about specific calendar events, meeting titles, or anything that could change
or be deleted later (e.g. "the user has a meeting called X") — those belong on the live calendar,
not in long-term memory, and would go stale the moment the event is edited or cancelled.

If yes: reply with ONE complete, self-contained sentence starting with "The user" that would make
sense on its own with no other context (e.g. "The user's name is Shubham." or "The user prefers
scheduling meetings in the morning.").

If no durable fact is present: reply with exactly the single word NONE.

Do not repeat these instructions. Do not add labels, prefixes, or explanations. Output only the
sentence or the word NONE.

User: {user_msg}
Assistant: {assistant_msg}"""


async def _recent_context_text(checkpointer, thread_id: str) -> str:
    try:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        state = await checkpointer.aget(config)
        if not state or "channel_values" not in state or "messages" not in state["channel_values"]:
            return "(no prior context)"
        recent = state["channel_values"]["messages"][-4:]
        lines = []
        for m in recent:
            if isinstance(m, HumanMessage):
                lines.append(f"User: {_truncate_for_classifier(str(m.content), 400)}")
            elif isinstance(m, AIMessage) and m.content:
                lines.append(f"Assistant: {_truncate_for_classifier(str(m.content), 400)}")
        return "\n".join(lines) if lines else "(no prior context)"
    except Exception:
        return "(no prior context)"


async def _passes_supervisor(message: str, context: str) -> bool:
    model = get_classifier_model()
    result = await model.ainvoke(
        [SystemMessage(content=_SUPERVISOR_PROMPT.format(
            context=_truncate_for_classifier(context),
            message=_truncate_for_classifier(message, 500),
        ))]
    )
    verdict = str(result.content).strip().upper()
    return "OUT_OF_SCOPE" not in verdict


async def _maybe_store_memory(oauth_user_id: str, user_msg: str, assistant_msg: str) -> None:
    try:
        model = get_classifier_model()
        result = await model.ainvoke(
            [SystemMessage(content=_MEMORY_EXTRACT_PROMPT.format(
                user_msg=_truncate_for_classifier(user_msg, 500),
                assistant_msg=_truncate_for_classifier(assistant_msg, 500),
            ))]
        )
        fact = str(result.content).strip()

        for marker in ("fact (or none):", "fact:", "answer:"):
            if fact.lower().startswith(marker):
                fact = fact[len(marker):].strip()

        if not fact or fact.upper().strip(".") == "NONE" or len(fact) < 8:
            return

        await add_memory_fact(oauth_user_id, fact)
    except Exception as e:
        print(f"[Memory Store Error] {e}")


async def stream_agent_reply(
    oauth_user_id: str,
    user_id: str,
    thread_id: str,
    message: str,
    attachments: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    yield {"type": "started", "message": "Checking request..."}

    checkpointer = await get_checkpointer()
    context = await _recent_context_text(checkpointer, thread_id)

    full_message = _build_message_content(message, attachments)

    try:
        await upsert_thread(thread_id, oauth_user_id, full_message)
    except Exception as e:
        print(f"[Thread Save Error] {e}")

    has_attachments = bool(attachments)
    if not has_attachments and not await _passes_supervisor(full_message, context):
        yield {"type": "token", "token": _OFF_TOPIC_REPLY}
        yield {"type": "completed", "message": "done"}
        return

    yield {"type": "progress", "message": "Thinking..."}

    calendar_tz = get_primary_calendar_timezone(oauth_user_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        memory_facts = await get_recent_facts(oauth_user_id)
    except Exception as e:
        print(f"[Memory Fetch Error] {e}")
        memory_facts = []

    full_reply = ""

    try:
        model = get_llm_model()
        tools = get_calendar_tools_for_user(oauth_user_id, user_id)

        agent = create_react_agent(
            model=model,
            tools=tools,
            checkpointer=checkpointer,
            prompt=SystemMessage(content=get_agent_instructions(now_iso, calendar_tz, memory_facts)),
        )

        run_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=full_message)]},
            version="v2",
            config=run_config,
        ):
            event_name = event.get("event")
            if event_name == "on_tool_start":
                yield {"type": "progress", "message": "Working on it..."}
            elif event_name == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    full_reply += text
                    yield {"type": "token", "token": text}
    except Exception as e:
        print(f"[Agent Run Error] {e}")
        yield {"type": "token", "token": _friendly_error(e)}
        yield {"type": "completed", "message": "done"}
        return

    try:
        await touch_thread(thread_id)
    except Exception as e:
        print(f"[Thread Touch Error] {e}")

    # Fire-and-forget: memory extraction is a nice-to-have, not something the user should
    # wait on. It previously ran with `await` before every "completed" event, adding a
    # full extra Groq round-trip of latency to every single reply (including "hi").
    import asyncio
    asyncio.create_task(_maybe_store_memory(oauth_user_id, full_message, full_reply))

    yield {"type": "completed", "message": "done"}


async def list_user_threads(oauth_user_id: str) -> List[Dict[str, Any]]:
    try:
        return await list_threads(oauth_user_id)
    except Exception as e:
        print(f"[Thread List Error] {e}")
        return []


async def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
    checkpointer = await get_checkpointer()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    state = await checkpointer.aget(config)
    if not state or "channel_values" not in state or "messages" not in state["channel_values"]:
        return []

    messages = state["channel_values"]["messages"]
    formatted = []
    for idx, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            formatted.append({"id": f"{thread_id}-{idx}", "role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage) and msg.content:
            formatted.append({"id": f"{thread_id}-{idx}", "role": "assistant", "content": str(msg.content)})
    return formatted


async def delete_user_thread(thread_id: str, oauth_user_id: str) -> None:
    await delete_thread_and_checkpoint(thread_id, oauth_user_id)
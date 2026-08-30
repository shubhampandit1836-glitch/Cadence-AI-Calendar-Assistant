import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from src.middleware.require_session import require_session
from src.config.rate_limiter import limiter
from src.services.agent_service import (
    stream_agent_reply,
    list_user_threads,
    get_thread_messages,
    delete_user_thread,
)

agent_router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatRequest(BaseModel):
    message: str
    threadId: str
    attachments: Optional[List[str]] = None


@agent_router.get("/threads")
async def get_threads(auth=Depends(require_session)):
    try:
        threads = await list_user_threads(auth["oauth_user_id"])
        return {"threads": threads}
    except Exception as e:
        print(f"[GET /threads Error] {e}")
        raise HTTPException(status_code=500, detail="Could not load your conversations. Please try again.")


@agent_router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, auth=Depends(require_session)):
    try:
        messages = await get_thread_messages(thread_id)
        return {"threadId": thread_id, "messages": messages}
    except Exception as e:
        print(f"[GET /threads/{{id}} Error] {e}")
        raise HTTPException(status_code=500, detail="Could not load this conversation. Please try again.")


@agent_router.post("/chat")
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, body: ChatRequest, auth=Depends(require_session)):
    async def event_generator():
        try:
            async for event in stream_agent_reply(
                auth["oauth_user_id"],
                auth["user_id"],
                body.threadId,
                body.message,
                attachments=body.attachments,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            print(f"[Chat Stream Error] {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Something went wrong. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive"},
    )


@agent_router.delete("/threads/{thread_id}")
async def delete_thread_route(thread_id: str, auth=Depends(require_session)):
    try:
        await delete_user_thread(thread_id, auth["oauth_user_id"])
        return {"deleted": True}
    except Exception as e:
        print(f"[DELETE /threads/{{id}} Error] {e}")
        raise HTTPException(status_code=500, detail="Could not delete this conversation. Please try again.")
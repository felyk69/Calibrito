import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.events import add_client, remove_client

router = APIRouter(prefix="/api/v1", tags=["Events"])


@router.get("/events")
async def sse_events(request: Request):
    queue = asyncio.Queue()
    add_client(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield f"data: {message}\n\n"
                except TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass
        finally:
            remove_client(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

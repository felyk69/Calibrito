import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.core.events import clients

router = APIRouter(prefix="/api", tags=["Events"])

@router.get("/events")
async def sse_events(request: Request):
    queue = asyncio.Queue()
    clients.add(queue)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass
        finally:
            clients.remove(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

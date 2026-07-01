from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
import asyncio
import os

from app.router import router

app = FastAPI(title="Shitstorm Moderation Service", version="2.0.0")
app.include_router(router)

# --- REDIS SSE CONFIGURATION ---
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def sse_generator(request: Request):
    redis_client = aioredis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    
    # NOTE: Changed to underscore to match your publisher!
    await pubsub.subscribe("thread_updates") 
    
    try:
        while True:
            if await request.is_disconnected():
                break
                
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message is not None and message["type"] == "message":
                data = message["data"].decode("utf-8")
                yield f"data: {data}\n\n"
            
            await asyncio.sleep(0.1)
    finally:
        await pubsub.unsubscribe("thread_updates")
        await redis_client.close()

@app.get("/moderation/schema-stream")
async def stream_schema(request: Request):
    return StreamingResponse(sse_generator(request), media_type="text/event-stream")
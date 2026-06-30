from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
import asyncio
import os

from .router import router

app = FastAPI(title="Group Project API")

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTERS ---
app.include_router(router)

# --- REDIS SSE CONFIGURATION ---
# Connect to Redis using the Docker service name
redis_url = os.getenv("REDIS_URL", "redis://redis:6379")

async def sse_generator(request: Request):
    """Generates SSE events from Redis Pub/Sub messages."""
    redis_client = aioredis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    
    # Subscribed to "thread-updates" to match your existing redis.py publisher
    await pubsub.subscribe("thread-updates")
    
    try:
        while True:
            # Check if the client closed the browser/tab
            if await request.is_disconnected():
                break
                
            # Use get_message with a timeout so we don't block infinitely
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message is not None and message["type"] == "message":
                data = message["data"].decode("utf-8")
                # SSE standard format requires 'data: ' prefix and '\n\n' suffix
                yield f"data: {data}\n\n"
            
            await asyncio.sleep(0.1) # Prevent CPU spinning
    finally:
        await pubsub.unsubscribe("thread-updates")
        await redis_client.close()

@app.get("/api/schema-stream")
async def stream_schema(request: Request):
    """Endpoint for the Vue frontend to connect to."""
    return StreamingResponse(sse_generator(request), media_type="text/event-stream")
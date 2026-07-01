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
    
    await pubsub.subscribe("thread_updates") 
    
    try:
        idle_time = 0
        while True:
            # 1. Prüfen, ob der User den Tab geschlossen hat
            if await request.is_disconnected():
                break
                
            # 2. Auf Nachrichten warten (wartet max 1 Sekunde)
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message is not None and message["type"] == "message":
                # Echte Daten gefunden!
                data = message["data"].decode("utf-8")
                yield f"data: {data}\n\n"
                idle_time = 0  # Timer zurücksetzen
            else:
                # Keine Nachricht erhalten, Timer erhöhen
                idle_time += 1
                
                # Wenn 15 Sekunden lang keine Nachricht kam, schicke einen Ping
                if idle_time >= 15:
                    yield ": ping\n\n"  # Ein SSE-Kommentar. Der Browser ignoriert ihn, hält aber die Leitung offen!
                    idle_time = 0
            
    finally:
        await pubsub.unsubscribe("thread_updates")
        await redis_client.close()

@app.get("/moderation/schema-stream")
async def stream_schema(request: Request):
    return StreamingResponse(sse_generator(request), media_type="text/event-stream")
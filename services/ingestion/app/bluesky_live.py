
#Author: Nassib Aboud
"""
bluesky_live.py
---------------
Streams live Bluesky comments, loads existing comments,
and fetches the original post text — all in one script.

Requirements:
    pip install websockets atproto pydantic httpx
"""
import os
import requests
import asyncio
import json
import re
from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone

import httpx
import websockets
from atproto import IdResolver
from atproto_client.models.string_formats import Handle
from pydantic import BaseModel
from .repositories.bluesky_repository import save_post, save_comment

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Comment(BaseModel):
    id: str
    text: str
    author: str
    parent_id: Optional[str] = None
    created_at: Optional[str] = None


class Post(BaseModel):
    id: str
    platform: str
    text: str
    comments: List[Comment] = []
    

#______________
#Input Variable
#______________

#url = input("Enter the Bluesky URL (post or account): ").strip()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PLATFORM = "bluesky"
JETSTREAM_URL = "wss://jetstream2.us-east.bsky.network/subscribe"
COLLECTION = "app.bsky.feed.post"
RECONNECT_DELAY = 3
BSKY_API_BASE = "https://public.api.bsky.app/xrpc"              # ← extracted
BSKY_THREAD_ENDPOINT = f"{BSKY_API_BASE}/app.bsky.feed.getPostThread"  # ← extracted

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

current_post: Optional[Post] = None
queue: asyncio.Queue[Comment] = asyncio.Queue()

# ---------------------------------------------------------------------------
# Link type
# ---------------------------------------------------------------------------

class Link(Enum):
    POST = "post"
    ACCOUNT = "account"


def check_link_type(url: str) -> Link:
    if re.search(r"profile/(.*?)/post/([\w]+)", url):
        return Link.POST
    return Link.ACCOUNT


def extract_post_info(url: str) -> tuple[str, str]:
    m = re.search(r"profile/(.*?)/post/([\w]+)", url)
    if not m:
        raise ValueError(f"Cannot extract post info from: {url}")
    return m.group(1), m.group(2)


def extract_handle(url: str) -> str:
    m = re.search(r"profile/([^/]+)", url)
    if not m:
        raise ValueError(f"Cannot extract handle from: {url}")
    return m.group(1)


def resolve_did(url: str) -> str:
    handle = extract_handle(url)
    print(f"  Resolving DID for @{handle} ...")
    resolver = IdResolver()
    did = resolver.handle.resolve(Handle(handle))
    if not did:
        raise ValueError(f"Could not resolve DID for handle: {handle}")
    print(f"  Resolved: {did}")
    return did


# ---------------------------------------------------------------------------
# REST: fetch post text + existing comments
# ---------------------------------------------------------------------------

def build_at_uri(handle: str, post_id: str) -> str:                      # ← new shared helper
    return f"at://{handle}/app.bsky.feed.post/{post_id}"

async def fetch_thread(handle: str, post_id: str, depth: int) -> dict:   # ← new shared helper
    uri = build_at_uri(handle, post_id)
    url = f"{BSKY_THREAD_ENDPOINT}?uri={uri}&depth={depth}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

async def fetch_post_text(handle: str, post_id: str) -> str:
    data = await fetch_thread(handle, post_id, depth=0)                   # ← uses helper
    return data["thread"]["post"]["record"]["text"]


async def fetch_existing_comments(handle: str, post_id: str) -> List[Comment]:
    data = await fetch_thread(handle, post_id, depth=1000)                # ← uses helper

    comments = []

    def parse_replies(replies: list):
        for reply in replies:
            if reply.get("$type") != "app.bsky.feed.defs#threadViewPost":
                continue
            post = reply.get("post", {})
            record = post.get("record", {})
            text = record.get("text", "").strip()
            if text:
                parent_uri = record.get("reply", {}).get("parent", {}).get("uri", "")
                parent_id = parent_uri.split("/")[-1] if parent_uri else None
                created_raw = record.get("createdAt")

                created_at = None

                if created_raw:
                    created_at = datetime.fromisoformat(
                        created_raw.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M:%S")

                comments.append(Comment(
                    id=post["uri"].split("/")[-1],
                    text=text,
                    author=post["author"]["did"],
                    parent_id=parent_id,
                    created_at=created_at,
                ))
            if reply.get("replies"):
                parse_replies(reply["replies"])

    parse_replies(data.get("thread", {}).get("replies", []))
    return comments

# ---------------------------------------------------------------------------
# Jetstream helpers
# ---------------------------------------------------------------------------

def build_ws_url(did: str | None) -> str:
    params = f"wantedCollections={COLLECTION}"
    if did:
        params += f"&wantedDids={did}"
    return f"{JETSTREAM_URL}?{params}"


def extract_reply_parent(record: dict) -> str | None:
    try:
        return record["reply"]["parent"]["uri"].split("/")[-1]
    except (KeyError, TypeError, AttributeError):
        return None


def extract_reply_root(record: dict) -> str | None:
    try:
        return record["reply"]["root"]["uri"].split("/")[-1]
    except (KeyError, TypeError, AttributeError):
        return None


def is_reply_to_post(record: dict, post_id: str) -> bool:
    return post_id in (extract_reply_root(record), extract_reply_parent(record))

# ---------------------------------------------------------------------------
# Consumer: queue → Post
# ---------------------------------------------------------------------------

async def comment_consumer():
    while True:
        comment: Comment = await queue.get()

        if current_post is not None:
            current_post.comments.append(comment)

            print("\n--- New Live Comment (ready for DB) ---")
            print(comment.model_dump_json(indent=2))
            print(f"  Post now has {len(current_post.comments)} comments total")
            await save_comment(comment, current_post.id)
            notify_api_comment_ingested(
                thread_id=current_post.id,
                comment_id=comment.id,
                )

        queue.task_done()

API_URL = os.getenv("API_URL", "http://api:8000")

def notify_api_comment_ingested(thread_id: str, comment_id: str):
    response = requests.post(
        f"{API_URL}/pipeline/bluesky/comment-ingested",
        json={
            "thread_id": thread_id,
            "comment_id": comment_id,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
# ---------------------------------------------------------------------------
# Producer: Jetstream WebSocket → queue
# ---------------------------------------------------------------------------

async def _stream_comments(ws_url: str, post_id: str | None = None):     # ← new shared core
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20) as ws:
                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if event.get("kind") != "commit":
                        continue
                    commit = event.get("commit", {})
                    if commit.get("operation") != "create":
                        continue
                    if commit.get("collection") != COLLECTION:
                        continue

                    record = commit.get("record", {})
                    text = record.get("text", "").strip()
                    if not text:
                        continue
                    if post_id and not is_reply_to_post(record, post_id):  # ← post filter only when needed
                        continue

                    created_raw = record.get("createdAt")

                    created_at = None

                    if created_raw:
                        created_at = datetime.fromisoformat(
                            created_raw.replace("Z", "+00:00")
                        ).strftime("%Y-%m-%d %H:%M:%S")

                    comment = Comment(
                        id=commit.get("rkey", ""),
                        text=text,
                        author=event.get("did", "unknown"),
                        parent_id=extract_reply_parent(record),
                        created_at=created_at,
                    )
                    await queue.put(comment)

        except websockets.exceptions.ConnectionClosed as e:
            print(f"  Connection closed ({e}), reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)
        except Exception as e:
            print(f"  Unexpected error: {e}, reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)


async def stream_post_comments(post_id: str):
    ws_url = build_ws_url(did=None)
    print(f"\n  Listening for new comments on post: {post_id}")
    print(f"  WebSocket: {ws_url}\n")
    print("-" * 60)
    await _stream_comments(ws_url, post_id=post_id)                       # ← delegates to shared core


async def stream_account_comments(did: str):
    ws_url = build_ws_url(did=did)
    print(f"\n  Listening for new comments from DID: {did}")
    print(f"  WebSocket: {ws_url}\n")
    print("-" * 60)
    await _stream_comments(ws_url)                                         # ← delegates to shared core

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_stream(url: str):
    global current_post

    url = url.strip()
    if not url:
        raise ValueError("URL is required")
    
    link_type = check_link_type(url)

    print(f"\nURL       : {url}")
    print(f"Link type : {link_type.value}")

    if link_type == Link.POST:
        handle, post_id = extract_post_info(url)
        print(f"Handle    : {handle}")
        print(f"Post ID   : {post_id}")

        # 1. Fetch post text
        print("\n  Fetching post text...")
        post_text = await fetch_post_text(handle, post_id)
        print(f"  Post text: {post_text}")

        # 2. Fetch existing comments
        print("\n  Fetching existing comments...")
        existing_comments = await fetch_existing_comments(handle, post_id)
        print(f"  Found {len(existing_comments)} existing comments")

        # 3. Build Post object with everything we have so far
        current_post = Post(
            id=post_id,
            platform=PLATFORM,
            text=post_text,
            comments=existing_comments,
        )

        print("\n--- Post snapshot (ready for DB) ---")
        print(current_post.model_dump_json(indent=2))
        await save_post(current_post)

        # 4. Start live stream for new comments
        print("\n  Starting live stream...\n")
        await asyncio.gather(
            stream_post_comments(post_id),
            comment_consumer(),
        )

    else:
        did = resolve_did(url)
        current_post = Post(id=did, platform=PLATFORM, text="")

        print("\n--- Account stream started ---")
        await asyncio.gather(
            stream_account_comments(did),
            comment_consumer(),
        )


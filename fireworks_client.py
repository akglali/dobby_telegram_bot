import os, json
import httpx

BASE = os.getenv("DOBBY_BASE", "https://api.fireworks.ai/inference/v1")
API_KEY = os.getenv("DOBBY_API_KEY")
MODEL  = os.getenv("DOBBY_MODEL")

if not API_KEY:
    raise RuntimeError("DOBBY_API_KEY is missing in .env")
if not MODEL:
    raise RuntimeError("DOBBY_MODEL is missing in .env")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

async def stream_chat_messages(messages: list[dict], temperature: float = 0.6, max_tokens: int = 512):
    """
    Stream a response from Fireworks (OpenAI-compatible) using a full message history.
    'messages' is a list like: [{"role": "system"/"user"/"assistant", "content": "..."}]
    Yields text deltas.
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    url = f"{BASE.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=HEADERS, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue

# Keep these exports for other parts of the app if needed 
__all__ = ["stream_chat_messages", "MODEL"]

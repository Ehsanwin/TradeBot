from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

class HttpClient:
    def __init__(self, timeout_sec: int = 10):
        self._client = httpx.AsyncClient(timeout=timeout_sec)

    async def get_json(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        r = await self._client.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    async def aclose(self):
        await self._client.aclose()

"""Cliente HTTP con cache en la tabla api_cache y límite de pedidos por segundo."""

import json
import sqlite3
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

# Parámetros que no forman parte de la clave del cache (credenciales).
_SECRET_PARAMS = {"api_key", "apikey", "token"}


def cache_key(url: str, params: Mapping[str, Any] | None = None) -> str:
    items = sorted((k, str(v)) for k, v in (params or {}).items() if k not in _SECRET_PARAMS)
    return url + ("?" + "&".join(f"{k}={v}" for k, v in items) if items else "")


class CachedHttp:
    """GET de JSON cacheado por (source, url+params). Un 404 se cachea como None."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        source: str,
        client: httpx.Client | None = None,
        min_interval: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.conn = conn
        self.source = source
        self.client = client or httpx.Client(timeout=20, follow_redirects=True)
        self.min_interval = min_interval
        self.sleep = sleep
        self._last = 0.0
        self.requests = 0  # pedidos reales hechos (útil en tests)

    def cached(self, url: str, params: Mapping[str, Any] | None = None) -> tuple[bool, Any]:
        row = self.conn.execute(
            "SELECT response FROM api_cache WHERE source = ? AND key = ?",
            (self.source, cache_key(url, params)),
        ).fetchone()
        return (False, None) if row is None else (True, json.loads(row[0]))

    def get_json(self, url: str, params: Mapping[str, Any] | None = None, *, use_cache: bool = True) -> Any:
        if use_cache:
            hit, value = self.cached(url, params)
            if hit:
                return value
        data = self._fetch(url, params)
        if use_cache:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO api_cache (source, key, response) VALUES (?, ?, ?)",
                    (self.source, cache_key(url, params), json.dumps(data)),
                )
        return data

    def get_bytes(self, url: str) -> bytes:
        self._throttle()
        resp = self.client.get(url)
        self.requests += 1
        resp.raise_for_status()
        return resp.content

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            self.sleep(wait)
        self._last = time.monotonic()

    def _fetch(self, url: str, params: Mapping[str, Any] | None) -> Any:
        for attempt in range(4):
            self._throttle()
            resp = self.client.get(url, params=dict(params or {}))
            self.requests += 1
            if resp.status_code == 429 and attempt < 3:
                self.sleep(float(resp.headers.get("Retry-After", 2 ** attempt)))
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("inalcanzable")

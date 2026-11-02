"""Minimal klient för Supabase REST (PostgREST). Bara standardbiblioteket."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections.abc import Callable

Opener = Callable[[urllib.request.Request], bytes]


def _default_open(req: urllib.request.Request) -> bytes:
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


class Supabase:
    def __init__(self, url: str | None = None, key: str | None = None, opener: Opener = _default_open):
        self.url = (url or os.environ["SUPABASE_URL"]).rstrip("/")
        self.key = key or os.environ["SUPABASE_SERVICE_KEY"]
        self.open = opener

    def _req(self, method: str, path: str, body=None, prefer: str | None = None, params: dict | None = None):
        q = ("?" + urllib.parse.urlencode(params, safe=",.()*:")) if params else ""
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        data = json.dumps(body).encode() if body is not None else None
        raw = self.open(urllib.request.Request(f"{self.url}/rest/v1/{path}{q}", data=data, method=method, headers=headers))
        return json.loads(raw) if raw else None

    def select(self, table: str, params: dict | None = None) -> list[dict]:
        return self._req("GET", table, params=params) or []

    def select_all(self, table: str, params: dict | None = None, page: int = 1000) -> list[dict]:
        out, offset = [], 0
        while True:
            rows = self.select(table, {**(params or {}), "limit": page, "offset": offset})
            out += rows
            if len(rows) < page:
                return out
            offset += page

    def upsert(self, table: str, rows: list[dict], on_conflict: str, batch: int = 1000) -> int:
        for i in range(0, len(rows), batch):
            self._req("POST", table, rows[i:i + batch], prefer="resolution=merge-duplicates,return=minimal",
                      params={"on_conflict": on_conflict})
        return len(rows)

    def insert(self, table: str, rows: list[dict] | dict, returning: bool = False):
        return self._req("POST", table, rows, prefer="return=representation" if returning else "return=minimal")

    def update(self, table: str, filters: dict, values: dict, returning: bool = True) -> list[dict]:
        return self._req("PATCH", table, values, prefer="return=representation" if returning else "return=minimal",
                         params=filters) or []

    def delete(self, table: str, filters: dict) -> None:
        self._req("DELETE", table, params=filters)

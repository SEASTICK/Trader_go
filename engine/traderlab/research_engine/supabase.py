"""Serveranslutning utan SDK. Hemligheter får aldrig förekomma i feltext."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

TABLES = ("candles", "funding_rates", "strategies", "hypotheses", "runs",
          "run_results", "run_trades", "research_members")


class ConnectionFailure(RuntimeError):
    """Avsiktligt begränsad feltext utan svarskropp, headers eller hemligheter."""


@dataclass(frozen=True)
class SupabaseStore:
    url: str
    secret_key: str = field(repr=False)
    timeout: float = 15

    def __post_init__(self):
        parsed = urlsplit(self.url)
        if (parsed.scheme != "https" or not parsed.hostname
                or not parsed.hostname.endswith(".supabase.co")
                or parsed.username or parsed.password or parsed.port
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise ValueError("SUPABASE_URL måste vara projektets HTTPS-adress på supabase.co")
        if not self.secret_key.startswith("sb_secret_") or any(c.isspace() for c in self.secret_key):
            raise ValueError("SUPABASE_SECRET_KEY måste vara en servernyckel av typen sb_secret_")

    @classmethod
    def from_env_file(cls, path: Path) -> SupabaseStore:
        mode = path.stat().st_mode
        credential_dir = os.environ.get("CREDENTIALS_DIRECTORY")
        # Systemd levererar credentials som read-only 0440 i en privat,
        # tjänstespecifik mount. Originalfilen utanför /run/credentials måste
        # fortfarande vara 0600/0400. Acceptera aldrig gruppskrivning/other-access.
        private_credential = bool(credential_dir) and (
            path.resolve().parent == Path(credential_dir).resolve()
            and str(path.resolve().parent).startswith("/run/credentials/")
            and mode & 0o227 == 0
        )
        if mode & 0o077 and not private_credential:
            raise ValueError("Miljöfilen får inte vara läsbar av grupp eller andra; använd chmod 600")
        values = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError("Felaktig rad i miljöfilen")
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return cls(values.get("SUPABASE_URL", ""), values.get("SUPABASE_SECRET_KEY", ""))

    def _get(self, table: str, query: dict) -> list[dict]:
        if table not in TABLES:
            raise ValueError("Okänd forskningstabell")
        request = Request(self.url.rstrip("/") + "/rest/v1/" + table + "?" + urlencode(query),
                          headers={"apikey": self.secret_key, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except HTTPError as exc:
            raise ConnectionFailure(f"Supabase {table}: HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise ConnectionFailure(f"Supabase {table}: nätverksfel") from None
        except (ValueError, UnicodeError):
            raise ConnectionFailure(f"Supabase {table}: ogiltigt JSON-svar") from None
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ConnectionFailure(f"Supabase {table}: oväntat svarsformat")
        return data

    def rpc(self, name: str, params: dict):
        if name not in {"research_claim", "research_heartbeat", "research_finish"}:
            raise ValueError("Okänd workerfunktion")
        return self._write("rpc/" + name, params)

    def insert_market_rows(self, table: str, rows: list[dict]):
        if table not in {"candles", "funding_rates"}:
            raise ValueError("Otillåten marknadsdatatabell")
        return self._write(table, rows, "resolution=ignore-duplicates,return=minimal")

    def _write(self, path: str, payload, prefer: str = "return=representation"):
        # Ingen automatisk retry: RPC:er kan ha committats trots tappat svar.
        request = Request(self.url.rstrip("/") + "/rest/v1/" + path,
                          data=json.dumps(payload, allow_nan=False).encode(), method="POST",
                          headers={"apikey": self.secret_key, "Content-Type": "application/json",
                                   "Prefer": prefer})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                return json.loads(body) if body else None
        except HTTPError as exc:
            raise ConnectionFailure(f"Supabase worker: HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise ConnectionFailure("Supabase worker: nätverksfel") from None

    def check_schema(self) -> dict[str, bool]:
        """Kontrollera tillgänglighet, utan att hämta användar- eller marknadsrader."""
        out = {}
        for table in TABLES:
            self._get(table, {"select": "*", "limit": 0})
            out[table] = True
        return out

    def closed_candles(self, *, provider: str, market: str, symbol: str,
                       interval: str, start: str, end: str) -> list[dict]:
        """Läs en tidsbegränsad serie. UTC-gränser och datakvalitet valideras av motorn.

        Nyckelbaserad paginering fungerar även när API:ts radgräns är lägre än 1000.
        Datasetet måste frysas och kontrollsummeras före forskningskörning.
        """
        query = {"select": "open_time,open,high,low,close,volume", "provider": "eq." + provider,
                 "market": "eq." + market, "symbol": "eq." + symbol,
                 "interval": "eq." + interval, "closed": "eq.true",
                 "and": f"(open_time.gte.{start},open_time.lt.{end})",
                 "order": "open_time.asc", "limit": 1000}
        rows = []
        while True:
            page = self._get("candles", query)
            if not page:
                return rows
            try:
                cursor = page[-1]["open_time"]
            except KeyError:
                raise ConnectionFailure("Supabase candles: tidsstämpel saknas") from None
            if rows and cursor == rows[-1]["open_time"]:
                raise ConnectionFailure("Supabase candles: pagineringen går inte framåt")
            rows.extend(page)
            query["open_time"] = "gt." + cursor

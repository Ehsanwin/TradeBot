from __future__ import annotations
from typing import List, Optional, Dict, Any
import json
import requests
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from ..types import NormalizedNews
from ..importance import map_importance


class ForexFactoryClient:
    def __init__(self, json_url: Optional[str], *, timezone_name: str = "UTC",
                 timeout: int = 15, retries: int = 2, backoff: float = 0.8, importance_default: int = 2):
        self.json_url = (json_url or "").strip() if json_url else None
        self.tz = timezone_name
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.importance_default = importance_default

    def _http_get_json(self, url: str) -> List[Dict[str, Any]]:
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200 and resp.text:
                    data = json.loads(resp.text)
                    if isinstance(data, dict):
                        if "events" in data and isinstance(data["events"], list):
                            return data["events"]
                        return list(data.values())[0] if data else []
                    elif isinstance(data, list):
                        return data
                    return []
                last_err = RuntimeError(f"HTTP {resp.status_code}")
            except Exception as e:
                last_err = e
            if attempt < self.retries:
                import time as _t
                _t.sleep((2 ** attempt) * self.backoff)
        if last_err:
            raise last_err
        return []

    def _to_unix(self, dt_str: Optional[str], ts: Optional[int]) -> Optional[int]:
        if isinstance(ts, (int, float)):
            return int(ts)
        if isinstance(ts, str) and ts.strip().isdigit():
            return int(ts.strip())
        if not dt_str:
            return None
        return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                tzname = self.tz or "UTC"
                try:
                    dt = dt.replace(tzinfo=ZoneInfo(tzname) if ZoneInfo else timezone.utc)
                except Exception:
                    dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            pass
        
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d %b %Y %H:%M", "%b %d, %Y %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                tzname = self.tz or "UTC"
                try:
                    dt = dt.replace(tzinfo=ZoneInfo(tzname) if ZoneInfo else timezone.utc)
                except Exception:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except Exception:
                pass
        return None
        
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        s = str(dt_str).strip()
        if s.lower() in {"all day", "all-day", "tba", "tbd", "-", ""}:
            return None
    def fetch(self) -> List[NormalizedNews]:
        if not self.json_url:
            return []

        rows = self._http_get_json(self.json_url)
        items: List[NormalizedNews] = []
        for r in rows:
            title = str(r.get("title") or r.get("event") or "").strip()
            impact = r.get("impact") or r.get("importance") or r.get("impact_text")
            country = r.get("country") or r.get("region")
            currency = r.get("currency")
            category = r.get("category") or r.get("event_type")
            url = r.get("url") or r.get("link")
            source_event_id = str(r.get("id") or r.get("event_id") or r.get("eid") or "")

            ts = r.get("timestamp") or r.get("ts") or r.get("unix")
            if not ts:
                ts_ms = r.get("timestamp_ms") or r.get("time_millis")
                if isinstance(ts_ms, (int, float)):
                    ts = int(ts_ms / 1000)
            
            date_val = r.get("date") or r.get("date_str") or r.get("day")
            time_val = r.get("time") or r.get("time_str") or r.get("time_label")
            if date_val and (not time_val or str(time_val).strip().lower() in {"all day","all-day","tba","tbd","-",""}):
                time_val = "00:00"
            
            dt_str = (
                r.get("datetime")
                or (f"{date_val} {time_val}".strip() if date_val and time_val else None)
                or None
            )
            t = self._to_unix(dt_str, ts)
            if t is None:

                continue

            importance = map_importance(impact, self.importance_default)
            body = r.get("detail") or r.get("description")
            if not body:
                actual = r.get("actual")
                forecast = r.get("forecast")
                previous = r.get("previous")
                parts = []
                if actual not in (None, ""): parts.append(f"Actual: {actual}")
                if forecast not in (None, ""): parts.append(f"Forecast: {forecast}")
                if previous not in (None, ""): parts.append(f"Previous: {previous}")
                body = "; ".join(parts) if parts else None

            items.append(NormalizedNews(
                t=t,
                source="forexfactory",
                title=title,
                importance=importance,
                body=body,
                country=country,
                currency=currency,
                category=category,
                url=url,
                source_event_id=source_event_id or None,
            ))
        return items

from __future__ import annotations
from typing import Optional, Iterable, Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import Symbol, Candle, NewsEvent

# ---------- Symbols ----------
def get_symbol_by_code(session: Session, code: str) -> Optional[Symbol]:
    return session.execute(select(Symbol).where(Symbol.code == code)).scalar_one_or_none()

def get_or_create_symbol(
    session: Session,
    *,
    code: str,
    display_symbol: Optional[str] = None,
    description: Optional[str] = None,
) -> Symbol:
    sym = get_symbol_by_code(session, code)
    if sym:
        return sym
    sym = Symbol(code=code, display_symbol=display_symbol, description=description)
    session.add(sym)
    session.flush()
    return sym

# ---------- Candles ----------
def upsert_candles(
    session: Session,
    *,
    symbol_id: int,
    resolution: str,
    rows: Iterable[Dict[str, Any]],
) -> int:
    payload = []
    for i, r in enumerate(rows):
        if "t" not in r:
            raise KeyError(f"row[{i}] missing 't'")
        t = r["t"]

        if not isinstance(t, int) or isinstance(t, bool):
            raise TypeError(f"row[{i}].t must be int (unix seconds); got {type(t).__name__}: {t!r}")

        payload.append({
            "symbol_id": symbol_id,
            "resolution": resolution,
            "ts": t,
            "open":   r.get("open", r.get("o")),
            "high":   r.get("high", r.get("h")),
            "low":    r.get("low",  r.get("l")),
            "close":  r.get("close",r.get("c")),
            "volume": r.get("volume", r.get("v")),
        })

    if not payload:
        return 0

    stmt = pg_insert(Candle).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol_id", "resolution", "ts"],
        set_={
            "open":   stmt.excluded.open,
            "high":   stmt.excluded.high,
            "low":    stmt.excluded.low,
            "close":  stmt.excluded.close,
            "volume": stmt.excluded.volume,
        },
    )
    res = session.execute(stmt)
    return res.rowcount or 0


# ---------- News (Economic Events) ----------
def _map_importance(x: Any) -> int:

    if isinstance(x, int):
        if x in (1, 2, 3):
            return x
        raise ValueError(f"importance int must be 1,2,3; got {x}")
    if not x:
        return 0
    s = str(x).strip().lower()
    if s in ("3", "high", "hi", "h", "red"):
        return 3
    if s in ("2", "medium", "med", "m", "orange"):
        return 2
    if s in ("1", "low", "lo", "l", "yellow"):
        return 1
    if s in ("none", "holiday", "bank holiday", "white", "non-economic"):
        return 0
    return 0

def upsert_news_events(
    session: Session,
    rows: Iterable[Dict[str, Any]],
) -> int:
    
    payload = []
    for i, r in enumerate(rows):
        if "t" not in r:
            raise KeyError(f"row[{i}] missing 't'")
        t = r["t"]
        if not isinstance(t, int) or isinstance(t, bool):
            raise TypeError(f"row[{i}].t must be int (unix seconds); got {type(t).__name__}: {t!r}")

        src = r.get("source")
        if not src or not isinstance(src, str):
            raise KeyError(f"row[{i}] missing 'source' (str)")

        title = r.get("title")
        if not title or not isinstance(title, str):
            raise KeyError(f"row[{i}] missing 'title' (str)")

        imp = _map_importance(r.get("importance"))

        payload.append({
            "source": src,
            "ts": t,
            "title": title[:256],
            "importance": imp,
            "body": r.get("body"),
            "country": r.get("country"),
            "currency": r.get("currency"),
            "category": r.get("category"),
            "url": r.get("url"),
            "source_event_id": r.get("source_event_id"),
        })

    if not payload:
        return 0

    stmt = pg_insert(NewsEvent).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "ts", "title"],
        set_={
            "importance": stmt.excluded.importance,
            "body": stmt.excluded.body,
            "country": stmt.excluded.country,
            "currency": stmt.excluded.currency,
            "category": stmt.excluded.category,
            "url": stmt.excluded.url,
            "source_event_id": stmt.excluded.source_event_id,
        },
    )
    res = session.execute(stmt)
    return res.rowcount or 0

def list_news_events(
    session,
    *,
    source: Optional[str] = None,
    min_importance: int = 0,
    from_ts: Optional[int] = None,
    to_ts: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    q = select(NewsEvent).order_by(NewsEvent.ts.asc())
    conds = []
    if source:
        conds.append(NewsEvent.source == source)
    if min_importance > 0:
        conds.append(NewsEvent.importance >= min_importance)
    if from_ts:
        conds.append(NewsEvent.ts >= from_ts)
    if to_ts:
        conds.append(NewsEvent.ts <= to_ts)
    if conds:
        q = q.where(and_(*conds))
    if limit:
        q = q.limit(limit)

    rows = session.execute(q).scalars().all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "source": r.source,
            "ts": r.ts,
            "title": r.title,
            "importance": r.importance,
            "body": r.body,
            "country": r.country,
            "currency": r.currency,
            "category": r.category,
            "url": r.url,
            "source_event_id": r.source_event_id,
        })
    return out
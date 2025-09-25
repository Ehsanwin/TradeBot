from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from .httpClient import FinnhubHTTP
from TradeBot.logger import get_logger

log = get_logger(__name__)

_ALLOWED_RESOLUTIONS = {"1", "5", "15", "30", "60", "D", "W", "M"}

def _ensure_unix(ts: Union[int, float, dt.datetime, dt.date]) -> int:
    if isinstance(ts, (int, float)):
        return int(ts)
    if isinstance(ts, dt.datetime):
        return int(ts.timestamp())
    if isinstance(ts, dt.date):
        return int(dt.datetime(ts.year, ts.month, ts.day).timestamp())
    raise TypeError("from/to must be int(timestamp) or datetime/date.")

def list_exchanges(client: FinnhubHTTP) -> List[str]:
    log.debug("list_exchanges()")
    data = client.get("/forex/exchange")
    out = data if isinstance(data, list) else list(data or [])
    log.debug("list_exchanges: %s exchanges", len(out))
    return out

def list_symbols(client: FinnhubHTTP, exchange: str) -> List[str]:
    log.debug("list_symbols(exchange=%s)", exchange)
    data = client.get("/forex/symbol", params={"exchange": exchange})
    out = data if isinstance(data, list) else list(data or [])
    log.debug("list_symbols: %s symbols for %s", len(out), exchange)
    return out

def all_rates(client: FinnhubHTTP, base: str = "USD", date: Optional[str] = None) -> Dict[str, Any]:
    log.debug("all_rates(base=%s, date=%s)", base, date)
    params: Dict[str, Any] = {"base": base}
    if date:
        params["date"] = date
    data = client.get("/forex/rates", params=params)
    log.debug("all_rates: keys=%s", list(data.keys())[:5])
    return data

def candles(
    client: FinnhubHTTP,
    symbol: str,
    resolution: str,
    start: Union[int, float, dt.datetime, dt.date],
    end: Union[int, float, dt.datetime, dt.date],
    as_df: bool = True,
    tz: Optional[str] = None,
) -> Union["pd.DataFrame", Dict[str, Any]]:
    log.debug("candles(symbol=%s, res=%s, start=%s, end=%s, as_df=%s, tz=%s)",
              symbol, resolution, start, end, as_df, tz)
    if resolution not in _ALLOWED_RESOLUTIONS:
        raise ValueError(f"invalid resolution: {resolution}. Allowed: {_ALLOWED_RESOLUTIONS}")
    _from = _ensure_unix(start)
    _to = _ensure_unix(end)

    data = client.get("/forex/candle", params={"symbol": symbol, "resolution": resolution, "from": _from, "to": _to})
    if not as_df or pd is None:
        return data
    if not data or data.get("s") != "ok":
        log.warning("candles: empty or non-ok response for %s (%s)", symbol, resolution)
        return pd.DataFrame()

    df = pd.DataFrame({
        "t": data.get("t", []),
        "o": data.get("o", []),
        "h": data.get("h", []),
        "l": data.get("l", []),
        "c": data.get("c", []),
        "v": data.get("v", []),
    })
    if not df.empty:
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df = df.set_index("t").sort_index()
        if tz:
            df.index = df.index.tz_convert(tz)  # type: ignore
        df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}, inplace=True)  # type: ignore
    log.debug("candles: %s rows for %s (%s)", len(df), symbol, resolution)
    return df  # type: ignore

def quote(client: FinnhubHTTP, symbol: str) -> Dict[str, Any]:
    log.debug("quote(symbol=%s)", symbol)
    data = client.get("/quote", params={"symbol": symbol})
    log.debug("quote: keys=%s", list(data.keys()))
    return data

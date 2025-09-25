from __future__ import annotations
from TradeBot.logger import get_logger

log = get_logger(__name__)

def map_importance(val, default_: int = 2) -> int:
    if isinstance(val, int):
        return val if val in (1, 2, 3) else default_

    if val is None:
        return default_

    s = str(val).strip().lower()
    if s in {"3", "high", "hi", "h", "red", "very high", "high impact"}:
        return 3
    if s in {"2", "medium", "med", "m", "orange", "moderate"}:
        return 2
    if s in {"1", "low", "lo", "l", "yellow", "minor"}:
        return 1

    log.debug("[news] importance fallback for value=%r -> %s", val, default_)
    return default_

from __future__ import annotations
import time
from typing import Optional, Any, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from TradeBot.logger import get_logger
log = get_logger(__name__)

def to_unix_utc(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp())

def rss_pubdate_to_unix(pubdate: Optional[str]) -> Optional[int]:
    if not pubdate:
        return None
    try:
        # Try RFC 2822 format first (standard RSS)
        dt = parsedate_to_datetime(pubdate)
        return to_unix_utc(dt)
    except Exception:
        try:
            # Try ISO 8601 format (YYYY-MM-DD HH:MM:SS)
            from datetime import datetime
            dt = datetime.fromisoformat(pubdate.replace('Z', '+00:00'))
            return to_unix_utc(dt)
        except Exception:
            try:
                # Try simple format (YYYY-MM-DD HH:MM:SS) 
                from datetime import datetime
                dt = datetime.strptime(pubdate, '%Y-%m-%d %H:%M:%S')
                return to_unix_utc(dt)
            except Exception as e:
                log.warning("[news] rss_pubdate_to_unix: parse failed for %r: %s", pubdate, e)
                return None

def rss_any_to_unix(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        import time as _t
        if hasattr(value, "tm_year") and hasattr(value, "tm_mon"):
            return int(_t.mktime(value))
    except Exception:
        pass

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return rss_any_to_unix(value[0] if len(value) else None)

    if isinstance(value, str):
        return rss_pubdate_to_unix(value)

    try:
        s = str(value).strip()
        return rss_pubdate_to_unix(s)
    except Exception:
        return None

def now_unix() -> int:
    return int(time.time())

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

from TradeBot.logger import get_logger
log = get_logger(__name__)

@dataclass
class NormalizedNews:
    t: int                     # Unix seconds (UTC)
    source: str                # 'investing' | 'forexfactory' | ...
    title: str
    importance: int            # 1=Low, 2=Medium, 3=High
    body: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    source_event_id: Optional[str] = None

    def as_row(self) -> Dict[str, object]:
        return {
            "t": self.t,
            "source": self.source,
            "title": self.title,
            "importance": self.importance,
            "body": self.body,
            "country": self.country,
            "currency": self.currency,
            "category": self.category,
            "url": self.url,
            "source_event_id": self.source_event_id,
        }

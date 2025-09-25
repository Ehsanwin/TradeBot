from __future__ import annotations
from typing import List

from TradeBot.config.setting_schema import TradingBotConfig
from .types import NormalizedNews
from .sources.investing_rss import InvestingRSSClient
from .sources.forexfactory import ForexFactoryClient
from .sources.chatgpt_news import ChatGPTNewsClient

from TradeBot.logger import get_logger
log = get_logger(__name__)

NEWS = TradingBotConfig().news

from TradeBot.database.session import get_session
from TradeBot.database.repositories import upsert_news_events

def _filter_upcoming(items: List[NormalizedNews], hours: int) -> List[NormalizedNews]:
    if hours <= 0:
        return items
    from .parser_utils import now_unix
    now = now_unix()
    end = now + hours * 3600
    res = [x for x in items if x.t is not None and now <= x.t <= end]
    log.debug("[news] filtered upcoming window=%sh -> kept=%s of %s", hours, len(res), len(items))
    return res

class NewsService:
    def __init__(self):
        self.enabled = NEWS.enabled
        self.sources = set(s.strip().lower() for s in (NEWS.sources or []))
        log.info("[news] init enabled=%s sources=%s", self.enabled, sorted(self.sources))

        self.clients = []
        if "chatgpt" in self.sources and NEWS.openai_api_key:
            log.debug("[news] enabling ChatGPT: model=%s, max_items=%s", NEWS.openai_model, NEWS.chatgpt_max_news_items)
            self.clients.append(
                ChatGPTNewsClient(
                    api_key=NEWS.openai_api_key,
                    model=NEWS.openai_model,
                    api_base=NEWS.openai_api_base,
                    timeout=NEWS.request_timeout,
                    retries=NEWS.retries,
                    backoff=NEWS.backoff,
                    importance_default=NEWS.importance_default,
                    max_news_items=NEWS.chatgpt_max_news_items,
                )
            )
        if "investing" in self.sources and NEWS.investing_rss_urls:
            log.debug("[news] enabling Investing RSS: %s", NEWS.investing_rss_urls)
            self.clients.append(
                InvestingRSSClient(
                    urls=NEWS.investing_rss_urls,
                    timeout=NEWS.request_timeout,
                    retries=NEWS.retries,
                    backoff=NEWS.backoff,
                    importance_default=NEWS.importance_default,
                )
            )
        if "forexfactory" in self.sources:
            log.debug("[news] enabling ForexFactory JSON url=%s tz=%s", NEWS.ff_export_json_url, NEWS.ff_timezone)
            self.clients.append(
                ForexFactoryClient(
                    json_url=NEWS.ff_export_json_url,
                    timezone_name=NEWS.ff_timezone,
                    timeout=NEWS.request_timeout,
                    retries=NEWS.retries,
                    backoff=NEWS.backoff,
                    importance_default=NEWS.importance_default,
                )
            )

    def fetch_all(self) -> List[NormalizedNews]:
        if not self.enabled:
            return []
        items: List[NormalizedNews] = []
        for c in self.clients:
            try:
                batch = c.fetch()
                before = len(batch)
                if NEWS.max_items_per_source and len(batch) > NEWS.max_items_per_source:
                    batch = batch[:NEWS.max_items_per_source]
                items.extend(batch)
                log.info("[news] %s fetched=%s (capped=%s) total=%s",
                         c.__class__.__name__, before, len(batch), len(items))
            except Exception:
                log.exception("[news] source %s failed", c.__class__.__name__)
        return items

    def persist(self, items: List[NormalizedNews]) -> int:
        if not items:
            log.info("[news] nothing to persist")
            return 0
        rows = [x.as_row() for x in items if x.t and x.title and x.source]
        if not rows:
            log.warning("[news] all rows invalid or missing core fields; skipped")
            return 0
        with get_session() as s:
            affected = upsert_news_events(s, rows=rows)
            log.info("[news] persisted rows=%s", affected)
            return affected

    def run_once(self) -> int:
        items = self.fetch_all()
        upcoming = _filter_upcoming(items, NEWS.upcoming_default_hours)
        return self.persist(upcoming or items)

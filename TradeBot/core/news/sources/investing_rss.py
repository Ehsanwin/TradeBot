from __future__ import annotations
from typing import List, Optional
import re
import requests

try:
    import feedparser
except Exception:
    feedparser = None

from ..types import NormalizedNews
from ..importance import map_importance
from ..parser_utils import rss_pubdate_to_unix, now_unix, rss_any_to_unix
from TradeBot.logger import get_logger

log = get_logger(__name__)

_IMPORTANCE_PATTERN = re.compile(r"\b(high|medium|low)\b", re.I)
_CURRENCY_PATTERN = re.compile(r"\b([A-Z]{3})\b")

class InvestingRSSClient:
    def __init__(self, urls: List[str], *, timeout: int = 15, retries: int = 2, backoff: float = 0.8, importance_default: int = 2):
        self.urls = [u.strip() for u in urls if u.strip()]
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.importance_default = importance_default
        log.debug("[news] InvestingRSSClient init urls=%s timeout=%s retries=%s", self.urls, timeout, retries)

    def _http_get(self, url: str) -> Optional[str]:
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                log.debug("[news] GET %s attempt=%s", url, attempt + 1)
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200 and resp.text:
                    return resp.text
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                log.warning("[news] GET %s status=%s", url, resp.status_code)
            except Exception as e:
                last_err = e
                log.warning("[news] GET %s failed: %s", url, e)
            if attempt < self.retries:
                import time as _t
                delay = (2 ** attempt) * self.backoff
                log.debug("[news] backoff sleep %ss", delay)
                _t.sleep(delay)
        if last_err:
            log.error("[news] GET %s exhausted: %s", url, last_err)
            raise last_err
        return None

    def _infer_importance(self, title: str, summary: str) -> int:
        for text in (title or "", summary or ""):
            m = _IMPORTANCE_PATTERN.search(text or "")
            if m:
                return map_importance(m.group(1), self.importance_default)
        return self.importance_default

    def _infer_currency(self, text: str) -> Optional[str]:
        m = _CURRENCY_PATTERN.search(text or "")
        return m.group(1) if m else None

    def fetch(self) -> List[NormalizedNews]:
        items: List[NormalizedNews] = []
        for url in self.urls:
            try:
                log.info("[news] Investing RSS fetch start url=%s", url)
                if feedparser:
                    parsed = feedparser.parse(url)
                    count = 0
                    for e in parsed.entries:
                        title = getattr(e, "title", "")
                        link = getattr(e, "link", None)
                        summary = getattr(e, "summary", "") or getattr(e, "description", "")
                        t = (
                            rss_any_to_unix(getattr(e, "published", None)) or
                            rss_any_to_unix(getattr(e, "updated", None)) or
                            rss_any_to_unix(getattr(e, "published_parsed", None)) or
                            rss_any_to_unix(getattr(e, "updated_parsed", None)) or
                            now_unix()
                        )

                        importance = self._infer_importance(title, summary)
                        currency = self._infer_currency(f"{title} {summary}")

                        items.append(NormalizedNews(
                            t=t,
                            source="investing",
                            title=title,
                            importance=importance,
                            body=summary,
                            currency=currency,
                            url=link,
                        ))
                        count += 1
                    log.info("[news] Investing RSS parsed entries=%s from %s", count, url)
                else:
                    xml = self._http_get(url)
                    if not xml:
                        continue
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(xml)
                    count = 0
                    for it in root.findall(".//item"):
                        title = (it.findtext("title") or "").strip()
                        link = (it.findtext("link") or "").strip()
                        summary = (it.findtext("description") or "").strip()
                        pubDate = (it.findtext("pubDate") or "").strip()
                        t = rss_pubdate_to_unix(pubDate) or now_unix()
                        importance = self._infer_importance(title, summary)
                        currency = self._infer_currency(f"{title} {summary}")

                        items.append(NormalizedNews(
                            t=t,
                            source="investing",
                            title=title,
                            importance=importance,
                            body=summary,
                            currency=currency,
                            url=link,
                        ))
                        count += 1
                    log.info("[news] Investing RSS (manual) parsed entries=%s from %s", count, url)
            except Exception:
                log.exception("[news] Investing RSS fetch failed url=%s", url)
        return items

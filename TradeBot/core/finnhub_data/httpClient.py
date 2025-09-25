from __future__ import annotations

import json
import random
import time
import requests
import logging
from dataclasses import dataclass
from typing import Optional, Any, Dict

from TradeBot.config.setting_schema import TradingBotConfig
from .exceptions import FinnhubAuthError, FinnhubHTTPError, FinnhubRateLimit
from TradeBot.logger import get_logger

log = get_logger(__name__)
config = TradingBotConfig()

class FinnhubHTTP:
    def __init__(
        self,
        *,
        base_url: Optional[str] = config.finnhub.api_base,
        token: Optional[str] = config.finnhub.api_token,
        timeout: int = config.finnhub.HTTP_TIMEOUT,
        retries: int = config.finnhub.HTTP_RETRIES,
        backoff: float = config.finnhub.HTTP_BACKOFF,
        proxies: Optional[Dict[str, str]] = None,
        session: Optional[requests.Session] = None
    ) -> None:
        if not token:
            raise FinnhubAuthError(
                "FINNHUB_API_TOKEN تعریف نشده است. آن را در conf/setting.py یا env تنظیم کنید."
            )
        self.base_url = base_url
        self.token = token
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.proxies = proxies
        # اگر session پاس داده نشده باشد، lazy init می‌کنیم تا اگر کسی فایل را ناقص import کرد، باز هم خراب نشود:
        self._session: Optional[requests.Session] = session  # ساخته نمی‌کنیم تا اولین درخواست

    # ------------- Context Manager -------------
    def __enter__(self) -> "FinnhubHTTP":
        self._ensure_session()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._session is not None:
                self._session.close()
        finally:
            self._session = None

    # ------------- Utilities -------------
    def _ensure_session(self) -> None:
        if self._session is None:
            self._session = requests.Session()

    def _sleep_backoff(self, attempt: int, retry_after: Optional[float] = None) -> None:
        if retry_after is not None:
            time.sleep(max(0.0, float(retry_after)))
            return
        delay = (2 ** attempt) * self.backoff
        delay = delay * (0.8 + random.random() * 0.4)  # ±20% jitter
        time.sleep(delay)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._ensure_session()
        assert self._session is not None  # برای MyPy/Type checkers

        params = params.copy() if params else {}
        params["token"] = self.token

        safe_params = {k: ("***" if k.lower() == "token" else v) for k, v in params.items()}
        url = f"{self.base_url}{path}"

        last_err: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                log.debug("HTTP %s %s params=%s attempt=%s", method.upper(), path, safe_params, attempt + 1)

                resp = self._session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    timeout=self.timeout,
                    proxies=self.proxies,
                )

                if resp.status_code == 401:
                    log.error("401 Unauthorized for %s", path)
                    raise FinnhubAuthError("Unauthorized (401) — توکن را بررسی کنید.")
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", "0") or 0)
                    if attempt < self.retries:
                        log.warning("429 Rate-Limit on %s — retry in %ss (attempt=%s)", path, retry_after or "backoff", attempt + 1)
                        self._sleep_backoff(attempt, retry_after if retry_after > 0 else None)
                        continue
                    raise FinnhubRateLimit("Rate limit exceeded (429).", retry_after=retry_after or None)

                if 400 <= resp.status_code < 600:
                    log.error("HTTP %s on %s: %s", resp.status_code, path, resp.text[:200])
                    raise FinnhubHTTPError(resp.status_code, resp.text)

                # OK
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    return {"raw": resp.text}

            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                if attempt < self.retries:
                    log.warning("Network error on %s: %s — retrying (attempt=%s)", path, e, attempt + 1)
                    self._sleep_backoff(attempt)
                    continue
                log.error("Network error after retries on %s: %s", path, e)
                raise FinnhubHTTPError(599, f"Network error after retries: {e}") from e

        if last_err:
            log.error("Exhausted retries for %s: %s", path, last_err)
            raise FinnhubHTTPError(599, f"Exhausted retries: {last_err}") from last_err
        raise FinnhubHTTPError(599, "Exhausted retries without specific error.")

    # ------------- Public API -------------
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", path, params=params or {})

    def close(self) -> None:
        """بستن session به‌صورت دستی (اگر از with استفاده نکردی)."""
        if self._session is not None:
            self._session.close()
            self._session = None
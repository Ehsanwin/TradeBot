from __future__ import annotations

import time

from TradeBot.config.setting_schema import TradingBotConfig
from .service import NewsService
from TradeBot.logger import setup_logging, get_logger

NEWS = TradingBotConfig().news
log = get_logger(__name__)

def main() -> None:
    setup_logging()
    svc = NewsService()

    if not svc.enabled:
        log.info("[news] disabled by config")
        return

    interval = max(1, int(NEWS.refresh_interval_min)) * 60
    log.info("[news] starting poller every %s min(s) ...", NEWS.refresh_interval_min)
    while True:
        try:
            cnt = svc.run_once()
            log.info("[news] upserted %s row(s)", cnt)
        except Exception:
            log.exception("[news] run failed")
        time.sleep(interval)

if __name__ == "__main__":
    main()

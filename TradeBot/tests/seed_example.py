from __future__ import annotations
from ..database.session import get_session
from ..database.repositories import get_or_create_symbol, upsert_candles, upsert_indicator_values

def main() -> None:
    with get_session() as s:
        sym = get_or_create_symbol(s, code="OANDA:EUR_USD", display_symbol="EUR/USD", description="EUR/USD")
        rows = [
            {"t": 1726524000, "o": 1.0912, "h": 1.0931, "l": 1.0895, "c": 1.0920, "v": 12345},
            {"t": 1726527600, "o": 1.0920, "h": 1.0950, "l": 1.0902, "c": 1.0942, "v": 15321},
        ]
        c = upsert_candles(s, symbol_id=sym.id, resolution="60", rows=rows)
        print("candles upserted:", c)

        rsi_rows = [
            {"t": 1726524000, "data": {"rsi": 48.2}},
            {"t": 1726527600, "data": {"rsi": 52.7}},
        ]
        i = upsert_indicator_values(s, symbol_id=sym.id, name="rsi", resolution="60", rows=rsi_rows)
        print("indicators upserted:", i)

if __name__ == "__main__":
    main()

from __future__ import annotations
import datetime as dt

from TradeBot.core.http_client import FinnhubHTTP
from TradeBot.core.finnhub import forex

def main() -> None:
    client = FinnhubHTTP()

    # --- Exchanges & Symbols
    exchanges = forex.list_exchanges(client)
    print(f"Exchanges: {exchanges[:5]}")
    if "OANDA" in exchanges:
        symbols = forex.list_symbols(client, "OANDA")
        print(f"Sample symbol: {(symbols[0] if symbols else None)}")
        sym = "OANDA:EUR_USD"
    else:
        sym = "OANDA:EUR_USD"  # fallback

    # --- Quote
    q = forex.quote(client, sym)
    print(f"Quote: {q}")

        # --- Rates
    rates = forex.all_rates(client, base="USD")
    print(f"Rates[USD->EUR]: {rates.get("quote", {}).get("EUR")}")

    # --- Candles
    start = int((dt.datetime.utcnow() - dt.timedelta(days=14)).timestamp())
    end = int(dt.datetime.utcnow().timestamp())
    df = forex.candles(client, symbol=sym, resolution="60", start=start, end=end, as_df=True, tz="UTC")
    print(f"Candles head:\n {df.head()}") # type: ignore


if __name__ == "__main__":
    main()
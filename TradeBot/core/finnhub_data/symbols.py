from __future__ import annotations
from typing import List, Dict, Any, Set

SYMBOLS: List[Dict[str, Any]] = [
    {
        "name": "GOLD",
        "role": ["primary", "api_list"],
        "aliases": {
            "oanda_code": "XAU_USD",
            "finnhub": "OANDA:XAU_USD"
        }
    },
    {
        "name": "DXY",
        "role": ["api_list", "correlated"],
        "aliases": {"finnhub": "PEPPERSTONE:10019"}
    },
    {
        "name": "SILVER",
        "role": ["api_list", "correlated"],
        "aliases": {
            "oanda_code": "XAG_USD",
            "finnhub": "OANDA:XAG_USD"
        }
    },
    {
        "name": "WTI",
        "role": ["api_list", "correlated"],
        "aliases": {
            "oanda_code": "WTICO_USD",
            "finnhub": "OANDA:WTICO_USD"
        }
    },
    {
        "name": "SP500",
        "role": ["api_list", "correlated"],
        "aliases": {
            "oanda_code": "SPX500_USD",
            "finnhub": "OANDA:SPX500_USD"
        }
    },
    {
        "name": "US10Y",
        "role": ["api_list", "correlated"],
        "aliases": {
            "oanda_code": "USB10Y_USD",
            "finnhub": "OANDA:USB10Y_USD"
        }
    },
    {
        "name": "EURUSD",
        "role": ["api_list", "correlated"],
        "aliases": {"oanda_code": "EUR_USD"}
    },
    {
        "name": "GBPUSD",
        "role": ["api_list", "correlated"],
        "aliases": {"oanda_code": "GBP_USD"}
    },
    {
        "name": "USDJPY",
        "role": ["api_list", "correlated"],
        "aliases": {"oanda_code": "USD_JPY"}
    },
]

def _mk_finnhub_symbol(entry: Dict[str, Any]) -> str | None:
    aliases = entry.get("aliases", {})

    fh = aliases.get("finnhub")
    if fh:
        return str(fh).strip()

    oc = aliases.get("oanda_code")
    if oc:
        return f"OANDA:{oc}".strip()
    
    ops = aliases.get("oanda_proxy_symbol")
    if ops:
        return f"OANDA:{ops}".strip()

    return None

NAME_TO_ENTRY: Dict[str, Dict[str, Any]] = {e["name"]: e for e in SYMBOLS}
NAME_TO_FINNHUB: Dict[str, str] = {e["name"]: _mk_finnhub_symbol(e) for e in SYMBOLS if _mk_finnhub_symbol(e)} # type: ignore

FINNHUB_TO_NAME: Dict[str, str] = {fh: name for name, fh in NAME_TO_FINNHUB.items()}

def finnhub_symbol_for_names(names: List[str]) -> List[str]:
    out: List[str] = []
    for n in names:
        key = (n or "").strip().upper()
        fh = NAME_TO_FINNHUB.get(key)
        if fh:
            out.append(fh)
    return out

def finnhub_symbols_for_roles(roles: Set[str]) -> List[str]:
    if not roles:
        roles = {"api_list"}
    out: List[str] = []
    role_lc = {r.strip().lower() for r in roles if r.strip()}
    for e in SYMBOLS:
        eroles = {r.strip().lower() for r in e.get("role", [])}
        if eroles & role_lc:
            fh = NAME_TO_FINNHUB.get(e["name"])
            if fh:
                out.append(fh)
    return out

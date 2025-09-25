from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Any, List, Dict, Optional, Tuple

# ---- env (dev-friendly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- logging (shared logger configured by project settings)
from TradeBot.logger import setup_logging, get_logger
setup_logging()
log = get_logger(__name__)

# ---- Flask API
from flask import Flask, jsonify, request

# ---- Project config (Pydantic schema)
from TradeBot.config.setting_schema import TradingBotConfig

# ---- Finnhub (HTTP client + feature modules)
from TradeBot.core.finnhub_data.httpClient import FinnhubHTTP
from TradeBot.core.finnhub_data import forex as fx
from TradeBot.core.finnhub_data.symbols import finnhub_symbols_for_roles, FINNHUB_TO_NAME, finnhub_symbol_for_names
from TradeBot.core.finnhub_data import technical_analysis as ta


_SYMBOLS_CACHE: Dict[str, Any] = {
    "age": 0,            # unix seconds
    "data": None         # {"OANDA": [...], "FXCM":[...], ...}
}
_SYMBOLS_CACHE_TTL = 60 * 60

# ---- News service (normalized + persist)
from TradeBot.core.news.service import NewsService

# ---- Database repository layer
from TradeBot.database.session import get_session
from TradeBot.database.repositories import (
    get_or_create_symbol,
    upsert_candles,
    upsert_news_events
)


# =========================================================
# Config
# =========================================================
CFG = TradingBotConfig()

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = (os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes"))

API_PREFIX = "/api/v1"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

PROM_ENABLE = (os.getenv("PROMETHEUS_ENABLED", "false").lower() in ("1", "true", "yes"))
PROM_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))
PROM_PATH = os.getenv("PROMETHEUS_METRICS_PATH", "/metrics")

# =========================================================
# Flask App
# =========================================================
app = Flask(__name__)

# --------------- Error handling ---------------
class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

@app.errorhandler(ApiError)
def _handle_api_error(err: ApiError):
    log.warning("ApiError %s: %s", err.status_code, err)
    resp = {"ok": False, "error": str(err), "details": err.details}
    return jsonify(resp), err.status_code

@app.errorhandler(Exception)
def _handle_exception(err: Exception):
    log.exception("Unhandled exception")
    resp = {"ok": False, "error": "internal_error"}
    return jsonify(resp), 500

def _require_params(params: Dict[str, Any], *names: str):
    missing = [n for n in names if params.get(n) in (None, "")]
    if missing:
        raise ApiError(f"missing required params: {', '.join(missing)}", 400)
    
# =========================================================
# Helpers
# =========================================================
def get_finnhub() -> FinnhubHTTP:
    return FinnhubHTTP(
        base_url=CFG.finnhub.api_base,
        token=CFG.finnhub.api_token,
        timeout=getattr(CFG.finnhub, "HTTP_TIMEOUT", 15),
        retries=getattr(CFG.finnhub, "HTTP_RETRIES", 3),
        backoff=getattr(CFG.finnhub, "HTTP_BACKOFF", 0.8),
    )

def _parse_int(v: Optional[str], name: str) -> int:
    if v is None or v == "":
        raise ApiError(f"missing required numeric params: {name}", 400)
    try:
        return int(v)
    except Exception:
        raise ApiError(f"invalid int for {name}: {v}", 400)

def _df_or_array_to_rows_candle(obj: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        import pandas as pd
        if hasattr(obj, "index") and hasattr(obj, "to_dict"):
            df = obj # type: ignore
            for ts, rec in df.iterrows():
                t = int(getattr(ts, "timestamp", lambda: 0)())
                rows.append(
                    {
                        "t": t,
                        "o": rec.get("open") or rec.get("o"),
                        "h": rec.get("high") or rec.get("h"),
                        "l": rec.get("low")  or rec.get("l"),
                        "c": rec.get("close") or rec.get("c"),
                        "v": rec.get("volume") or rec.get("v"),
                    }
                )
            return rows
    except Exception:
        pass

    if isinstance(obj, dict):
        t = obj.get("t") or []
        o = obj.get("o") or obj.get("open") or []
        h = obj.get("h") or obj.get("high") or []
        l = obj.get("l") or obj.get("low") or []
        c = obj.get("c") or obj.get("close") or []
        v = obj.get("v") or obj.get("volume") or []
        n = min(len(t), len(o), len(h), len(l), len(c), len(v))
        for i in range(n):
            ti = t[i]
            if not isinstance(ti, int):
                try:
                    ti = int(ti)
                except Exception:
                    continue
            
            rows.append(
                {
                    "t": ti,
                    "o": o[i],
                    "h": h[i],
                    "l": l[i],
                    "c": c[i],
                    "v": v[i]
                }
            )
        return rows
    return rows


# =========================================================
# Routes
# =========================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "env": ENVIRONMENT
        }
    )

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "ok": True,
        "message": "TradeBot API Server",
        "env": ENVIRONMENT,
        "api_prefix": API_PREFIX,
        "available_endpoints": [
            f"{API_PREFIX}/forex/exchanges",
            f"{API_PREFIX}/forex/symbols", 
            f"{API_PREFIX}/forex/quote",
            f"{API_PREFIX}/forex/candles",
            f"{API_PREFIX}/technical/support-resistance",
            f"{API_PREFIX}/technical/patterns",
            f"{API_PREFIX}/technical/analysis",
            f"{API_PREFIX}/news/fetch",
            f"{API_PREFIX}/news/list",
            f"{API_PREFIX}/news/chatgpt/generate",
            f"{API_PREFIX}/news/chatgpt/config",
            f"{API_PREFIX}/news/chatgpt/bulk",
            f"{API_PREFIX}/news/chatgpt/summary",
            f"{API_PREFIX}/news/chatgpt/health"
        ]
    })

@app.route(f"{API_PREFIX}/debug/routes", methods=["GET"])
def debug_routes():
    """Debug endpoint to list all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "rule": rule.rule
        })
    return jsonify({
        "ok": True,
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x['rule'])
    })

# ---------- Forex ----------
@app.route(f"{API_PREFIX}/forex/exchanges", methods=["GET"])
def api_forex_exchange():
    with get_finnhub() as client:
        data = fx.list_exchanges(client)
    return jsonify(
        {
            "ok": True,
            "data": data
        }
    )

@app.route(f"{API_PREFIX}/forex/symbols", methods=["GET"])
def api_forex_symbol():
    fmt = (request.args.get("format", "finnhub") or "details").strip().lower()
    names_csv = request.args.get("names")
    roles_csv = request.args.get("roles") or os.getenv("SYMBOLS_DEFAULT_ROLES", "api_list")

    if names_csv:
        wanted_names = {n.strip().upper() for n in names_csv.split(",") if n.strip()}
        finnhub_syms = finnhub_symbol_for_names(list(wanted_names))
    else:
        roles = {r.strip().lower() for r in roles_csv.split(",") if r.strip()}
        finnhub_syms = finnhub_symbols_for_roles(roles)

    if fmt == "flat":
        return jsonify({"ok": True, "symbols": finnhub_syms})
    
    data = [{"name": FINNHUB_TO_NAME.get(s, s), "finnhub": s} for s in finnhub_syms]
    return jsonify({"ok": True, "count": len(data), "data": data})

@app.route(f"{API_PREFIX}/forex/quote", methods=["GET"])
def api_forex_quote():
    q = request.args
    symbols_csv = q.get("symbols_csv")
    names_csv = q.get("names")
    roles_csv = q.get("roles") or os.getenv("SYMBOLS_DEFAULT_ROLES", "api_list")

    if symbols_csv:
        final_symbols = [s.strip() for s in symbols_csv.split(",") if s.strip()]
    elif names_csv:
        wanted_names = [s.strip().upper() for s in names_csv.split(",") if s.strip()]
        final_symbols = finnhub_symbol_for_names(wanted_names)
    else:
        roles = [s.strip().lower() for s in roles_csv.split(",") if s.strip()]
        final_symbols = finnhub_symbols_for_roles(roles)
    
    if not final_symbols:
        raise ApiError("no symbols selected (check names/roles)", 400)
    
    out: Dict[str, Dict[str, Any]] = {}
    errors: Dict[str, str] = {}
    with get_finnhub() as client:
        for sym in final_symbols:
            try:
                out[sym] = client.get("/quote", params={"symbol": sym})
            except Exception as e:
                errors[sym] = str(e)
                log.warning("quote failed for %s: %s", sym, e)
    data = [{"name": FINNHUB_TO_NAME.get(code, code), "symbol": code, "quote": out.get(code)} for code in final_symbols]
    return jsonify({"ok": True, "requested": len(final_symbols), "errors": errors, "data": data})

@app.route(f"{API_PREFIX}/forex/candles", methods=["GET"])
def api_forex_candles():
    q = request.args
    
    # Default resolution: 15-minute candles
    resolution = q.get("resolution", "15")
    
    # Default time range: last 24 hours
    import time
    now = int(time.time())
    default_start = now - (24 * 60 * 60)  # 24 hours ago
    
    start = q.get("from", str(default_start))
    end = q.get("to", str(now))

    try:
        start_i = int(start)
        end_i = int(end)
    except Exception:
        raise ApiError("invalid int for from/to parameters", 400)
    
    # Validate time range
    if start_i >= end_i:
        raise ApiError("'from' timestamp must be less than 'to' timestamp", 400)
    
    # Validate resolution
    valid_resolutions = {"1", "5", "15", "30", "60", "D", "W", "M"}
    if resolution not in valid_resolutions:
        raise ApiError(f"invalid resolution '{resolution}'. Valid options: {', '.join(valid_resolutions)}", 400)

    save = (q.get("save", "0").lower() in ("1", "true", "yes"))
    symbols_csv = q.get("symbols")
    names_csv = q.get("names")
    roles_csv = q.get("roles") or os.getenv("SYMBOLS_DEFAULT_ROLES", "api_list")

    if symbols_csv:
        final_symbols = [s.strip() for s in symbols_csv.split(",") if s.strip()]
    elif names_csv:
        wanted_names = [s.strip().upper() for s in names_csv.split(",") if s.strip()]
        final_symbols = finnhub_symbol_for_names(wanted_names)
    else:
        roles = {s.strip().lower() for s in roles_csv.split(",") if s.strip()}
        final_symbols = finnhub_symbols_for_roles(roles)

    if not final_symbols:
        raise ApiError("no symbols selected (check names/roles)", 400)

    results: Dict[str, int] = {}
    saves: Dict[str, int] = {}
    errors: Dict[str, str] = {}

    with get_finnhub() as client:
        for code in final_symbols:
            try:
                raw = client.get("/forex/candle", params={
                    "symbol": code,
                    "resolution": resolution,
                    "from": start_i,
                    "to": end_i,
                })
                rows: List[Dict[str, Any]] = []
                if isinstance(raw, dict) and raw.get("s") == "ok":
                    t = raw.get("t", [])
                    o = raw.get("o", []); h = raw.get("h", []); l = raw.get("l", []); c = raw.get("c", []); v = raw.get("v", [])
                    n = min(len(t), len(o), len(h), len(l), len(c), len(v))
                    for i in range(n):
                        try:
                            ti = int(t[i])
                        except Exception:
                            continue
                        rows.append({"t": ti, "o": o[i], "h": h[i], "l": l[i], "c": c[i], "v": v[i]})
                results[code] = len(rows)

                if save and rows:
                    from TradeBot.database.repositories import get_or_create_symbol, upsert_candles
                    from TradeBot.database.session import get_session
                    with get_session() as s:
                        disp = FINNHUB_TO_NAME.get(code, code)
                        sym_row = get_or_create_symbol(s, code=code, display_symbol=disp, description=None)
                        saves[code] = upsert_candles(s, symbol_id=sym_row.id, resolution=resolution, rows=rows)
            except Exception as e:
                errors[code] = str(e)
                log.warning("candles failed for %s: %s", code, e)

    data = [{"name": FINNHUB_TO_NAME.get(code, code), "symbol": code, "rows": results.get(code, 0)} for code in final_symbols]
    return jsonify({"ok": True, "requested": len(final_symbols), "data": data, "saved": saves, "errors": errors})

# ---------- Technical Analysis ----------
@app.route(f"{API_PREFIX}/technical/support-resistance", methods=["GET"])
def api_support_resistance():
    """Get support and resistance levels for a symbol."""
    q = request.args
    symbol = q.get("symbol")
    resolution = q.get("resolution", "15")
    
    if not symbol:
        raise ApiError("missing required parameter: symbol", 400)
    
    # Validate resolution
    valid_resolutions = {"1", "5", "15", "30", "60", "D", "W", "M"}
    if resolution not in valid_resolutions:
        raise ApiError(f"invalid resolution '{resolution}'. Valid options: {', '.join(valid_resolutions)}", 400)
    
    # Optional time range parameters
    days_back = q.get("days", "100")
    try:
        days_back_i = int(days_back)
        if days_back_i <= 0:
            raise ValueError("days must be positive")
    except (ValueError, TypeError):
        raise ApiError(f"invalid days parameter: {days_back}", 400)
    
    # Calculate start/end times
    import datetime as dt
    end_time = dt.datetime.now()
    start_time = end_time - dt.timedelta(days=days_back_i)
    
    try:
        with get_finnhub() as client:
            levels = ta.support_resistance_levels(
                client, symbol, resolution, start_time, end_time
            )
            
        return jsonify({
            "ok": True,
            "symbol": symbol,
            "resolution": resolution,
            "days_analyzed": days_back_i,
            "analysis_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "support_levels": levels.get("support", []),
            "resistance_levels": levels.get("resistance", []),
            "support_count": len(levels.get("support", [])),
            "resistance_count": len(levels.get("resistance", []))
        })
        
    except Exception as e:
        log.error("Support/resistance analysis failed for %s: %s", symbol, e)
        raise ApiError(f"Technical analysis failed: {str(e)}", 500)

@app.route(f"{API_PREFIX}/technical/patterns", methods=["GET"])
def api_pattern_recognition():
    """Get pattern recognition for a symbol."""
    q = request.args
    symbol = q.get("symbol")
    resolution = q.get("resolution", "15")
    use_fallback = (q.get("fallback", "true").lower() in ("1", "true", "yes"))
    
    if not symbol:
        raise ApiError("missing required parameter: symbol", 400)
    
    # Validate resolution
    valid_resolutions = {"1", "5", "15", "30", "60", "D", "W", "M"}
    if resolution not in valid_resolutions:
        raise ApiError(f"invalid resolution '{resolution}'. Valid options: {', '.join(valid_resolutions)}", 400)
    
    # Optional time range for fallback detection
    days_back = q.get("days", "50")
    try:
        days_back_i = int(days_back)
        if days_back_i <= 0:
            raise ValueError("days must be positive")
    except (ValueError, TypeError):
        raise ApiError(f"invalid days parameter: {days_back}", 400)
    
    try:
        with get_finnhub() as client:
            patterns = ta.pattern_recognition(client, symbol, resolution)
            
            # If no patterns found and fallback is enabled, try simple detection
            if not patterns.get("points") and use_fallback:
                import datetime as dt
                end_time = dt.datetime.now()
                start_time = end_time - dt.timedelta(days=days_back_i)
                
                log.info("No API patterns found for %s, trying simple detection", symbol)
                simple_patterns = ta.simple_pattern_detection(
                    client, symbol, resolution, start_time, end_time
                )
                
                if simple_patterns.get("points"):
                    patterns["fallback_patterns"] = simple_patterns
                    log.info("Found %d patterns using simple detection", len(simple_patterns["points"]))
            
        # Format pattern data
        api_patterns = patterns.get("points", [])
        fallback_patterns = patterns.get("fallback_patterns", {}).get("points", [])
        all_patterns = api_patterns + fallback_patterns
        
        response_data = {
            "ok": True,
            "symbol": symbol,
            "resolution": resolution,
            "pattern_count": len(all_patterns),
            "api_patterns": api_patterns,
            "api_pattern_count": len(api_patterns),
            "has_patterns": len(all_patterns) > 0,
            "endpoint_used": patterns.get("endpoint_used"),
            "fallback_used": len(fallback_patterns) > 0
        }
        
        # Include all patterns in main patterns field for backward compatibility
        response_data["patterns"] = all_patterns
        
        # Add fallback patterns separately if they exist
        if fallback_patterns:
            response_data["fallback_patterns"] = fallback_patterns
            response_data["fallback_pattern_count"] = len(fallback_patterns)
            response_data["fallback_method"] = patterns.get("fallback_patterns", {}).get("method")
        
        return jsonify(response_data)
        
    except Exception as e:
        log.error("Pattern recognition failed for %s: %s", symbol, e)
        raise ApiError(f"Pattern recognition failed: {str(e)}", 500)

@app.route(f"{API_PREFIX}/technical/analysis", methods=["GET"])
def api_combined_analysis():
    """Get combined technical analysis (support/resistance + patterns)."""
    q = request.args
    symbol = q.get("symbol")
    resolution = q.get("resolution", "15")
    
    if not symbol:
        raise ApiError("missing required parameter: symbol", 400)
    
    # Validate resolution
    valid_resolutions = {"1", "5", "15", "30", "60", "D", "W", "M"}
    if resolution not in valid_resolutions:
        raise ApiError(f"invalid resolution '{resolution}'. Valid options: {', '.join(valid_resolutions)}", 400)
    
    # Optional time range parameters
    days_back = q.get("days", "100")
    try:
        days_back_i = int(days_back)
        if days_back_i <= 0:
            raise ValueError("days must be positive")
    except (ValueError, TypeError):
        raise ApiError(f"invalid days parameter: {days_back}", 400)
    
    # Calculate start/end times
    import datetime as dt
    end_time = dt.datetime.now()
    start_time = end_time - dt.timedelta(days=days_back_i)
    
    try:
        with get_finnhub() as client:
            analysis = ta.get_analysis(
                client, symbol, resolution, start_time, end_time
            )
            
        # Add some additional metadata
        sr_data = analysis.get("support_resistance", {})
        pattern_data = analysis.get("patterns", {})
        
        # Get current price for context
        current_price = None
        try:
            with get_finnhub() as client:
                quote_data = fx.quote(client, symbol)
                current_price = quote_data.get("c")  # current price
        except Exception as e:
            log.warning("Could not get current price for %s: %s", symbol, e)
        
        # Calculate nearest levels if we have current price
        nearest_levels = {}
        if current_price and sr_data:
            supports = sr_data.get("support", [])
            resistances = sr_data.get("resistance", [])
            
            # Find nearest support (highest support below current price)
            supports_below = [s for s in supports if s < current_price]
            if supports_below:
                nearest_support = max(supports_below)
                distance_pct = ((current_price - nearest_support) / current_price) * 100
                nearest_levels["nearest_support"] = {
                    "level": nearest_support,
                    "distance_percentage": round(distance_pct, 2)
                }
            
            # Find nearest resistance (lowest resistance above current price)  
            resistances_above = [r for r in resistances if r > current_price]
            if resistances_above:
                nearest_resistance = min(resistances_above)
                distance_pct = ((nearest_resistance - current_price) / current_price) * 100
                nearest_levels["nearest_resistance"] = {
                    "level": nearest_resistance,
                    "distance_percentage": round(distance_pct, 2)
                }
        
        return jsonify({
            "ok": True,
            "symbol": symbol,
            "resolution": resolution,
            "current_price": current_price,
            "days_analyzed": days_back_i,
            "analysis_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "timestamp": analysis.get("timestamp"),
            "support_resistance": sr_data,
            "patterns": pattern_data,
            "nearest_levels": nearest_levels,
            "summary": {
                "support_count": len(sr_data.get("support", [])),
                "resistance_count": len(sr_data.get("resistance", [])),
                "api_pattern_count": len(pattern_data.get("points", [])),
                "fallback_pattern_count": len(pattern_data.get("fallback_patterns", {}).get("points", [])),
                "total_pattern_count": len(pattern_data.get("points", [])) + len(pattern_data.get("fallback_patterns", {}).get("points", [])),
                "has_patterns": (len(pattern_data.get("points", [])) + len(pattern_data.get("fallback_patterns", {}).get("points", []))) > 0,
                "fallback_used": len(pattern_data.get("fallback_patterns", {}).get("points", [])) > 0,
                "pattern_count": len(pattern_data.get("points", [])) + len(pattern_data.get("fallback_patterns", {}).get("points", []))  # Backward compatibility
            }
        })
        
    except Exception as e:
        log.error("Combined technical analysis failed for %s: %s", symbol, e)
        raise ApiError(f"Technical analysis failed: {str(e)}", 500)

# ---------- News ----------
@app.route(f"{API_PREFIX}/news/fetch", methods=["POST", "GET"])
def api_news_fetch():
    persist = (request.args.get("persist", "true").lower() in ("1", "true", "yes"))
    svc = NewsService()
    items = svc.fetch_all()
    saved = svc.persist(items) if persist else 0
    return jsonify(
        {
            "ok": True,
            "fetched": len(items),
            "saved": saved
        }
    )

@app.route(f"{API_PREFIX}/news/list", methods=["GET"])
def api_news_list():
    source = request.args.get("source")
    min_imp = int(request.args.get("min_importance", "0"))
    from_ts = request.args.get("from_ts")
    to_ts = request.args.get("to_ts")
    limit = int(request.args.get("limit", "100"))
    from_ts_i = int(from_ts) if from_ts else None
    to_ts_i = int(to_ts) if to_ts else None

    from TradeBot.database.repositories import list_news_events
    with get_session() as s:
        rows = list_news_events(s, source=source, min_importance=min_imp, from_ts=from_ts_i, to_ts=to_ts_i, limit=limit)
    return jsonify(
        {
            "ok": True,
            "fetched": len(rows),
            "data": rows
        }
    )

# ---------- ChatGPT News Endpoints ----------
@app.route(f"{API_PREFIX}/news/chatgpt/generate", methods=["POST", "GET"])
def api_chatgpt_news_generate():
    """Generate fresh news using ChatGPT"""
    q = request.args if request.method == "GET" else request.get_json() or {}
    
    # Configuration parameters
    api_key = q.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApiError("OpenAI API key required. Set OPENAI_API_KEY or provide 'api_key' parameter", 400)
    
    model = q.get("model", "gpt-4o-mini")
    max_items = int(q.get("max_items", "10"))
    persist = q.get("persist", True)
    use_web_search = q.get("use_web_search", "true")
    if isinstance(use_web_search, str):
        use_web_search = use_web_search.lower() in ("1", "true", "yes")
    if isinstance(persist, str):
        persist = persist.lower() in ("1", "true", "yes")
    
    # Validate parameters
    if max_items <= 0 or max_items > 50:
        raise ApiError("max_items must be between 1 and 50", 400)
    
    try:
        from TradeBot.core.news.sources.chatgpt_news import ChatGPTNewsClient
        
        # Create ChatGPT client with custom parameters
        client = ChatGPTNewsClient(
            api_key=api_key,
            model=model,
            timeout=30,
            retries=3,
            backoff=1.0,
            importance_default=2,
            max_news_items=max_items,
            use_web_search=use_web_search,
        )
        
        log.info("[api] Generating ChatGPT news: model=%s, max_items=%s", model, max_items)
        
        # Generate news
        news_items = client.fetch()
        
        if not news_items:
            return jsonify({
                "ok": True,
                "generated": 0,
                "saved": 0,
                "data": [],
                "message": "No news items generated"
            })
        
        # Convert to response format
        news_data = []
        for item in news_items:
            news_data.append({
                "title": item.title,
                "body": item.body,
                "source": item.source,
                "importance": item.importance,
                "country": item.country,
                "currency": item.currency,
                "category": item.category,
                "timestamp": item.t,
                "url": item.url,
                "source_event_id": item.source_event_id
            })
        
        # Optionally save to database
        saved_count = 0
        if persist:
            try:
                from TradeBot.core.news.service import NewsService
                svc = NewsService()
                saved_count = svc.persist(news_items)
                log.info("[api] Saved %s ChatGPT news items to database", saved_count)
            except Exception as e:
                log.warning("[api] Failed to save ChatGPT news to database: %s", e)
        
        return jsonify({
            "ok": True,
            "generated": len(news_items),
            "saved": saved_count,
            "model_used": model,
            "web_search": bool(use_web_search),

            "data": news_data,
            "generation_timestamp": int(time.time())
        })
        
    except Exception as e:
        log.error("[api] ChatGPT news generation failed: %s", e)
        raise ApiError(f"ChatGPT news generation failed: {str(e)}", 500)

@app.route(f"{API_PREFIX}/news/chatgpt/config", methods=["GET"])
def api_chatgpt_news_config():
    """Get ChatGPT news configuration and test API key"""
    api_key = request.args.get("api_key") or os.getenv("OPENAI_API_KEY")
    test_key = request.args.get("test", "false").lower() in ("1", "true", "yes")
    
    config_info = {
        "api_key_set": bool(api_key),
        "api_key_length": len(api_key) if api_key else 0,
        "default_model": "gpt-4o-mini",
        "supported_models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ],
        "max_items_limit": 50,
        "default_max_items": 10
    }
    
    # Test API key if requested
    key_valid = None
    if test_key and api_key:
        try:
            from TradeBot.core.news.sources.chatgpt_news import ChatGPTNewsClient
            test_client = ChatGPTNewsClient(
                api_key=api_key,
                model="gpt-4o-mini",
                max_news_items=1,
                timeout=10
            )
            # Try to make a small request to test the key
            test_items = test_client.fetch()
            key_valid = True
            config_info["test_result"] = "API key is valid"
            config_info["test_items_generated"] = len(test_items)
        except Exception as e:
            key_valid = False
            config_info["test_result"] = f"API key test failed: {str(e)}"
            log.warning("[api] ChatGPT API key test failed: %s", e)
    
    config_info["key_valid"] = key_valid
    
    return jsonify({
        "ok": True,
        "config": config_info
    })

@app.route(f"{API_PREFIX}/news/chatgpt/bulk", methods=["POST"])
def api_chatgpt_news_bulk():
    """Generate multiple batches of ChatGPT news with different parameters"""
    data = request.get_json() or {}
    
    api_key = data.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApiError("OpenAI API key required", 400)
    
    batches = data.get("batches", [])
    if not batches or not isinstance(batches, list):
        raise ApiError("'batches' array required with batch configurations", 400)
    
    if len(batches) > 10:
        raise ApiError("Maximum 10 batches allowed per request", 400)
    
    results = []
    total_generated = 0
    total_saved = 0
    
    persist = data.get("persist", True)
    if isinstance(persist, str):
        persist = persist.lower() in ("1", "true", "yes")
    
    try:
        from TradeBot.core.news.sources.chatgpt_news import ChatGPTNewsClient
        from TradeBot.core.news.service import NewsService
        
        svc = NewsService() if persist else None
        
        for i, batch_config in enumerate(batches):
            try:
                model = batch_config.get("model", "gpt-4o-mini")
                max_items = int(batch_config.get("max_items", "10"))
                batch_name = batch_config.get("name", f"batch_{i+1}")
                
                if max_items <= 0 or max_items > 50:
                    raise ValueError(f"max_items must be between 1 and 50, got {max_items}")
                
                log.info("[api] Processing batch %s: model=%s, max_items=%s", batch_name, model, max_items)
                
                # Create client for this batch
                client = ChatGPTNewsClient(
                    api_key=api_key,
                    model=model,
                    timeout=30,
                    retries=3,
                    max_news_items=max_items
                )
                
                # Generate news
                news_items = client.fetch()
                
                # Save if requested
                saved_count = 0
                if persist and svc and news_items:
                    saved_count = svc.persist(news_items)
                
                batch_result = {
                    "batch_name": batch_name,
                    "model": model,
                    "requested_items": max_items,
                    "generated": len(news_items),
                    "saved": saved_count,
                    "success": True,
                    "data": [
                        {
                            "title": item.title,
                            "importance": item.importance,
                            "country": item.country,
                            "currency": item.currency,
                            "category": item.category,
                            "timestamp": item.t
                        }
                        for item in news_items
                    ]
                }
                
                results.append(batch_result)
                total_generated += len(news_items)
                total_saved += saved_count
                
            except Exception as e:
                log.error("[api] Batch %s failed: %s", i+1, e)
                results.append({
                    "batch_name": batch_config.get("name", f"batch_{i+1}"),
                    "success": False,
                    "error": str(e)
                })
        
        return jsonify({
            "ok": True,
            "batches_processed": len(results),
            "total_generated": total_generated,
            "total_saved": total_saved,
            "results": results,
            "generation_timestamp": int(time.time())
        })
        
    except Exception as e:
        log.error("[api] ChatGPT bulk news generation failed: %s", e)
        raise ApiError(f"Bulk news generation failed: {str(e)}", 500)

@app.route(f"{API_PREFIX}/news/chatgpt/summary", methods=["GET"])
def api_chatgpt_news_summary():
    """Get summary of ChatGPT-generated news from database"""
    # Time range parameters
    hours_back = int(request.args.get("hours", "24"))
    min_importance = int(request.args.get("min_importance", "1"))
    
    if hours_back <= 0 or hours_back > 24*30:  # Max 30 days
        raise ApiError("hours parameter must be between 1 and 720 (30 days)", 400)
    
    if min_importance < 1 or min_importance > 3:
        raise ApiError("min_importance must be between 1 and 3", 400)
    
    # Calculate time range
    import time
    now = int(time.time())
    start_time = now - (hours_back * 3600)
    
    try:
        from TradeBot.database.repositories import list_news_events
        
        with get_session() as s:
            # Get ChatGPT news items
            rows = list_news_events(
                s, 
                source="chatgpt", 
                min_importance=min_importance,
                from_ts=start_time,
                to_ts=now,
                limit=1000
            )
        
        if not rows:
            return jsonify({
                "ok": True,
                "summary": {
                    "total_items": 0,
                    "time_range_hours": hours_back,
                    "min_importance": min_importance
                },
                "data": []
            })
        
        # Analyze the data
        categories = {}
        countries = {}
        currencies = {}
        importance_counts = {1: 0, 2: 0, 3: 0}
        
        for row in rows:
            # Count by category
            category = row.get("category") or "Unknown"
            categories[category] = categories.get(category, 0) + 1
            
            # Count by country
            country = row.get("country") or "Unknown"
            countries[country] = countries.get(country, 0) + 1
            
            # Count by currency
            currency = row.get("currency") or "Unknown"
            currencies[currency] = currencies.get(currency, 0) + 1
            
            # Count by importance
            importance = row.get("importance", 1)
            importance_counts[importance] = importance_counts.get(importance, 0) + 1
        
        # Sort by count
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]
        top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]
        top_currencies = sorted(currencies.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            "ok": True,
            "summary": {
                "total_items": len(rows),
                "time_range_hours": hours_back,
                "min_importance": min_importance,
                "analysis_period": {
                    "start_timestamp": start_time,
                    "end_timestamp": now,
                    "start_iso": datetime.fromtimestamp(start_time).isoformat(),
                    "end_iso": datetime.fromtimestamp(now).isoformat()
                },
                "importance_distribution": {
                    "high": importance_counts[3],
                    "medium": importance_counts[2], 
                    "low": importance_counts[1]
                },
                "top_categories": dict(top_categories),
                "top_countries": dict(top_countries),
                "top_currencies": dict(top_currencies),
                "unique_categories": len(categories),
                "unique_countries": len(countries),
                "unique_currencies": len(currencies)
            },
            "recent_items": rows[:20]  # Show first 20 items
        })
        
    except Exception as e:
        log.error("[api] ChatGPT news summary failed: %s", e)
        raise ApiError(f"News summary failed: {str(e)}", 500)

@app.route(f"{API_PREFIX}/news/chatgpt/health", methods=["GET"])
def api_chatgpt_news_health():
    """Health check for ChatGPT news functionality"""
    health_status = {
        "timestamp": int(time.time()),
        "checks": {}
    }
    
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    health_status["checks"]["api_key_available"] = {
        "status": "pass" if api_key else "fail",
        "message": "OpenAI API key is set" if api_key else "OpenAI API key not found in environment"
    }
    
    # Check if openai package is installed
    try:
        import openai
        health_status["checks"]["openai_package"] = {
            "status": "pass",
            "message": f"OpenAI package available (version: {openai.__version__})"
        }
    except ImportError:
        health_status["checks"]["openai_package"] = {
            "status": "fail", 
            "message": "OpenAI package not installed"
        }
    
    # Check database connectivity
    try:
        with get_session() as s:
            # Simple query to test database
            from TradeBot.database.repositories import list_news_events
            list_news_events(s, limit=1)
        health_status["checks"]["database"] = {
            "status": "pass",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "fail",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Check if we can create a ChatGPT client (without making API calls)
    if api_key:
        try:
            from TradeBot.core.news.sources.chatgpt_news import ChatGPTNewsClient
            ChatGPTNewsClient(api_key=api_key, max_news_items=1)
            health_status["checks"]["client_creation"] = {
                "status": "pass",
                "message": "ChatGPT client can be created"
            }
        except Exception as e:
            health_status["checks"]["client_creation"] = {
                "status": "fail",
                "message": f"ChatGPT client creation failed: {str(e)}"
            }
    else:
        health_status["checks"]["client_creation"] = {
            "status": "skip",
            "message": "Skipped due to missing API key"
        }
    
    # Determine overall health
    failed_checks = [k for k, v in health_status["checks"].items() if v["status"] == "fail"]
    health_status["overall_status"] = "healthy" if not failed_checks else "unhealthy"
    health_status["failed_checks"] = failed_checks
    
    # Set HTTP status based on health
    status_code = 200 if not failed_checks else 503
    
    return jsonify({
        "ok": not failed_checks,
        "health": health_status
    }), status_code

# ---------- Prometheus ----------
try:
    if PROM_ENABLE:
        from prometheus_client import CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
        REGISTRY = CollectorRegistry()
        @app.route(PROM_PATH, methods=["GET"])
        def metric():
            data = generate_latest()
            return app.response_class(data, mimetype=CONTENT_TYPE_LATEST)
except Exception as e:
    log.warning("Prometheus disabled: %s", e)

# =========================================================
# Background job: periodic news fetch
# =========================================================
def _news_loop():
    try:
        svc = NewsService()
        if not svc.enabled:
            log.info("[news] background loop disabled by config")
            return
        interval_sec = max(1, int(CFG.news.refresh_interval_min)) * 60
        log.info("[news] background loop every %s min", CFG.news.refresh_interval_min)
        while True:
            try:
                cnt = svc.run_once()
                log.info("[news] background loop upserted=%s", cnt)
            except Exception:
                log.exception("[news] background run failed")
            time.sleep(interval_sec)
    except Exception:
        log.exception("[news] background loop crashed")

def start_background_job():
    if os.getenv("NEWS_BG_LOOP", "true").lower() in ("1", "true", "yes"):
        t = threading.Thread(target=_news_loop, name="news-bg", daemon=True)
        t.start()

# =========================================================
# Entrypoint
# =========================================================
if __name__ == "__main__":
    start_background_job()
    log.info("Starting Flask on %s:%s (debug=%s, env=%s)", FLASK_HOST, FLASK_PORT, True, ENVIRONMENT)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)

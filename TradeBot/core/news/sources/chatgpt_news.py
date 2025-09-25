from __future__ import annotations
from typing import List, Optional, Dict, Any
import json
import time
from datetime import datetime, timezone
from TradeBot.logger import get_logger

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..types import NormalizedNews

log = get_logger(__name__)

class ChatGPTNewsClient:
    """ChatGPT-based news client that generates relevant financial news"""
    
    def __init__(
        self, 
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        api_base: str = "https://api.openai.com/v1",
        timeout: int = 30,
        retries: int = 3,
        backoff: float = 1.0,
        importance_default: int = 2,
        max_news_items: int = 10,
        use_web_search: bool = True,
    ):

        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        if not OpenAI:
            raise ImportError("openai package is required. Install with: pip install openai")
        

        self.client = OpenAI(api_key=api_key, base_url=api_base, timeout=timeout)
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.importance_default = importance_default
        self.max_news_items = max_news_items
        
        self.has_responses = hasattr(self.client, "responses")
        self.use_web_search = bool(use_web_search and self.has_responses)
        log.info(f"[news] ChatGPT client initialized: model={model}, max_items={max_news_items}")
    
    def _generate_news_prompt(self) -> str:
        """Generate prompt for ChatGPT to create financial news"""
        current_time = datetime.now(timezone.utc)
        
        return f"""You are an economic calendar agent. Use web search to fetch REAL data from ForexFactory official JSON endpoints (domain: nfs.faireconomy.media) and forexfactory.com. Avoid fabricating.

            Current UTC time: {current_time.isoformat()}

            Siurces to query:
            -htpps://nfs.faireconomy.media/calendar/latest.json
            -https://www.forexfactory.com/calendar.json
            -https://nfs.faireconomy.media/ff_calendar_thisweek.json
            Return ONLY events/items that could impact currency markets, including:
            - Central bank decisions and speeches
            - Economic indicators (GDP, inflation, employment)
            - Geopolitical events affecting currencies
            - Trade deals and agreements
            - Market-moving company earnings from major multinational corporations
            - Commodity price movements affecting resource currencies

            For each item, provide the following in JSON format(array only):
            {{
            "title": "Brief headline (max 100 characters)",
            "body": "Detailed description (max 300 characters)", 
            "importance": 1-3 (1=Low, 2=Medium, 3=High impact on forex),
            "country": "Country code (US, EU, JP, GB, AU, etc.)",
            "currency": "Primary affected currency code (USD, EUR, JPY, GBP, AUD, etc.)",
            "category": "Category (Central Bank, Economic Data, Geopolitical, Corporate, etc.)",
            "timestamp": "ISO 8601 timestamp in the last 24th (or upcoming in the next 24th)",
            "source": "full source url from forexfactory domain if available"
            }}

            Deduplicate by (title, timestamp).Return ONLY a JSON arayy of up to {self.max_news_items} items, no additional text."""
    
    def _call_chatgpt(self, prompt: str) -> Optional[str]:
        """Call OpenAI. Prefer Responses API + web_search; fallback to chat.completions."""
        last_error = None
        
        for attempt in range(self.retries + 1):
            try:
                log.debug(f"[news] ChatGPT API call attempt {attempt + 1}")
                if self.use_web_search:
                    
                    request_params = self.client.responses.create(
                        model=self.model,
                        input=[
                            {"role": "system", "content": "You are a professional ForexFactory crawler. Use web search to fetch official JSON from nfs.faireconomy.media / forexfactory.com only. Do not invent data. Return only a JSON array of items."},
                            {"role": "user", "content": prompt}
                        ],
                        tools=[{
                            "type": "web_search_preview"
                        }],
                        temperature=0.2,
                        max_output_tokens=2000,
                        response_format={"type": "json_object"}
                    )
                    text = get_text(request_params, "output_text", None)
                    if not text and hasattr(response, "output") and response.output:
                        try:
                            text = response.output[0].content[0].text  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    if text:
                        return text
                    try:
                        parsed = response.output[0].parsed  # type: ignore[attr-defined]
                        if parsed:
                            return json.dumps(parsed)
                    except Exception:
                        pass
                    log.warning("[news] Responses API returned no text; falling back to chat.completions")

                    return None
            except Exception as e:
                last_error = e
                log.warning("[news] ChatGPT call failed (attempt %d/%d): %s",
                                 attempt + 1, self.retries, e)
                # backoff
                if attempt < self.retries:
                    time.sleep(self.backoff * (2 ** attempt))

        log.error("[news] All attempts failed. last_error=%r", last_error)
        return None

    
    def _parse_news_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse ChatGPT JSON response into news items"""
        try:
            # Clean response - sometimes model adds markdown fences
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            news_data = json.loads(cleaned)
            
            if not isinstance(news_data, list):
                log.warning("[news] ChatGPT response is not a list")
                return []
            
            log.info(f"[news] Parsed {len(news_data)} news items from ChatGPT")
            return news_data
            
        except json.JSONDecodeError as e:
            log.error(f"[news] Failed to parse ChatGPT JSON response: {e}")
            log.debug(f"[news] Raw response: {response}")
            return []
        except Exception as e:
            log.error(f"[news] Error processing ChatGPT response: {e}")
            return []
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[int]:
        """Parse ISO timestamp string to Unix timestamp"""
        try:
            if not timestamp_str:
                return None
            
            # Handle various ISO formats
            timestamp_str = timestamp_str.strip()
            
            # Parse ISO format
            if 'T' in timestamp_str:
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(timestamp_str)
            else:
                # Assume it's just a date, add current time
                dt = datetime.fromisoformat(f"{timestamp_str}T{datetime.now().strftime('%H:%M:%S')}+00:00")
            
            # Ensure timezone is UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return int(dt.timestamp())
            
        except Exception as e:
            log.warning(f"[news] Failed to parse timestamp '{timestamp_str}': {e}")
            # Return current time as fallback
            return int(datetime.now(timezone.utc).timestamp())
    
    def _validate_importance(self, importance: Any) -> int:
        """Validate and normalize importance value"""
        try:
            val = int(importance)
            if 1 <= val <= 3:
                return val
        except (ValueError, TypeError):
            pass
        
        log.debug(f"[news] Invalid importance value '{importance}', using default {self.importance_default}")
        return self.importance_default
    
    def fetch(self) -> List[NormalizedNews]:
        """Fetch news from ChatGPT and return normalized news items"""
        log.info("[news] Fetching news from ChatGPT...")
        
        try:
            # Generate prompt and call ChatGPT
            prompt = self._generate_news_prompt()
            response = self._call_chatgpt(prompt)
            
            if not response:
                log.warning("[news] No response from ChatGPT")
                return []
            
            # Parse response
            news_items = self._parse_news_response(response)
            if not news_items:
                log.warning("[news] No valid news items parsed from ChatGPT response")
                return []
            
            # Convert to NormalizedNews objects
            normalized_items: List[NormalizedNews] = []
            
            for item in news_items:
                try:
                    # Extract and validate fields
                    title = str(item.get('title', '')).strip()
                    if not title:
                        log.debug("[news] Skipping item with empty title")
                        continue
                    
                    body = str(item.get('body', '')).strip() or None
                    importance = self._validate_importance(item.get('importance'))
                    country = str(item.get('country', '')).strip().upper() or None
                    currency = str(item.get('currency', '')).strip().upper() or None
                    category = str(item.get('category', '')).strip() or None
                    timestamp = self._parse_timestamp(str(item.get('timestamp', '')))
                    
                    # Create normalized news item
                    normalized_item = NormalizedNews(
                        t=timestamp,
                        source="chatgpt",
                        title=title,
                        importance=importance,
                        body=body,
                        country=country,
                        currency=currency,
                        category=category,
                        url=None,  # ChatGPT doesn't provide URLs
                        source_event_id=f"chatgpt_{int(time.time())}_{len(normalized_items)}"
                    )
                    
                    normalized_items.append(normalized_item)
                    log.debug(f"[news] Created normalized news item: {title}")
                    
                except Exception as e:
                    log.warning(f"[news] Error processing news item: {e}")
                    continue
            
            log.info(f"[news] ChatGPT fetch completed: {len(normalized_items)} items")
            return normalized_items
            
        except Exception as e:
            log.error(f"[news] ChatGPT fetch failed: {e}")
            return []

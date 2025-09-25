from __future__ import annotations

import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """Represents a single chat message"""
    role: str  # "system", "user", "assistant"
    content: str

@dataclass  
class ChatResponse:
    """Represents OpenAI chat completion response"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    
class OpenAIHTTPClient:
    """HTTP client for OpenAI ChatGPT API with retry logic and error handling"""
    
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        timeout: int = 30,
        retries: int = 3,
        backoff: float = 1.0
    ):
        if not api_key:
            raise ValueError("OpenAI API key is required")
            
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        
        # Configure session with retry strategy
        self.session = requests.Session()
        
        # Setup retry strategy
        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
            backoff_factor=backoff,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LLM-Trading-Bot/1.0"
        })
        
    def chat_completion(
        self,
        messages: List[ChatMessage],
        model: str = "gpt-4o-mini",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatResponse:
        """
        Send chat completion request to OpenAI API
        
        Args:
            messages: List of chat messages
            model: Model to use (default: gpt-4o-mini)
            max_tokens: Maximum tokens in response
            temperature: Model temperature (0-2)
            **kwargs: Additional parameters for the API
            
        Returns:
            ChatResponse object with the completion
            
        Raises:
            requests.exceptions.RequestException: For HTTP errors
            ValueError: For API errors or invalid responses
        """
        url = f"{self.api_base}/chat/completions"
        
        # Convert messages to dict format
        messages_dict = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        payload = {
            "model": model,
            "messages": messages_dict,
            **kwargs
        }
        
        # Skip temperature and max_tokens parameters for gpt-4o models to avoid API errors
        # These models have restrictions on parameter customization
        
        logger.debug(f"Sending chat completion request: model={model}, messages={len(messages)}, max_tokens={max_tokens}")
        
        try:
            start_time = time.time()
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            elapsed = time.time() - start_time
            
            logger.debug(f"OpenAI API response: status={response.status_code}, elapsed={elapsed:.2f}s")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', '60'))
                logger.warning(f"Rate limited, retrying after {retry_after}s")
                raise requests.exceptions.RetryError(f"Rate limited, retry after {retry_after}s")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Validate response structure
            if "choices" not in data or not data["choices"]:
                raise ValueError("Invalid OpenAI API response: missing choices")
            
            choice = data["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                raise ValueError("Invalid OpenAI API response: missing message content")
            
            return ChatResponse(
                content=choice["message"]["content"],
                model=data.get("model", model),
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "unknown")
            )
            
        except requests.exceptions.Timeout:
            logger.error(f"OpenAI API timeout after {self.timeout}s")
            raise
        except requests.exceptions.ConnectionError:
            logger.error("OpenAI API connection error")  
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenAI API HTTP error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                    raise ValueError(f"OpenAI API error: {error_msg}")
                except (json.JSONDecodeError, KeyError):
                    raise ValueError(f"OpenAI API error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from OpenAI API: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI API call: {e}")
            raise
    
    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Convenience function for creating system prompts
def create_system_prompt(role: str, context: str = "") -> ChatMessage:
    """Create a system message with predefined role and context"""
    
    base_prompts = {
        "trading_analyst": """You are an expert forex trading analyst with deep knowledge of technical analysis, fundamental analysis, and market psychology. You analyze market data and provide clear, actionable trading insights.

Your analysis should be:
- Data-driven and objective
- Risk-aware and conservative
- Clear and concise
- Focused on actionable insights

Always consider multiple timeframes, market context, news impact, and risk management in your analysis.""",
        
        "news_analyst": """You are a financial news analyst specializing in forex markets. You analyze economic news and events to determine their potential impact on currency pairs.

Your analysis should:
- Identify key market-moving events
- Assess impact severity and duration
- Consider market expectations vs reality
- Explain correlation with currency movements
- Highlight time-sensitive opportunities or risks""",
        
        "risk_manager": """You are a professional risk management specialist for forex trading. You assess and quantify risks in trading opportunities.

Your risk assessment should:
- Quantify potential downside and upside
- Identify key risk factors and scenarios
- Recommend position sizing and risk limits
- Consider correlation and portfolio impact
- Provide contingency plans for adverse scenarios""",
        
        "market_reporter": """You are a professional market analyst creating concise, informative market reports for traders and investors.

Your reports should be:
- Clear and well-structured
- Highlight key market themes and drivers
- Include actionable insights
- Professional but accessible tone
- Focus on what matters most for decision-making"""
    }
    
    prompt = base_prompts.get(role, f"You are a {role}.")
    if context:
        prompt += f"\n\nAdditional context: {context}"
    
    return ChatMessage(role="system", content=prompt)

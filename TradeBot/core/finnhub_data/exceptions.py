from typing import Optional

class FinnhubError(Exception):
    """General Error Finnhub."""
    pass

class FinnhubAuthError(FinnhubError):
    """Authentication problem (invalid or inactive token)."""
    pass

class FinnhubRateLimit(FinnhubError):
    """Blocked due to Rate Limit (Code 429)."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after

class FinnhubHTTPError(FinnhubError):
    """Other HTTP errors."""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code

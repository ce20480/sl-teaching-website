import logging
import time
from threading import Lock
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Implements a rate limiter for API calls to prevent 429 Too Many Requests errors.
    Uses a token bucket algorithm to limit request rates.
    """
    
    def __init__(self, max_requests: int = 5, refill_rate: float = 1.0, refill_interval: float = 1.0):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of tokens in the bucket (max burst size)
            refill_rate: Number of tokens to add per refill_interval
            refill_interval: Time in seconds between token refills
        """
        self.max_tokens = max_requests
        self.tokens = max_requests
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.last_refill_time = time.time()
        self.lock = Lock()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill_time
        
        # Calculate how many tokens to add based on elapsed time
        refill_count = (elapsed / self.refill_interval) * self.refill_rate
        
        if refill_count > 0:
            self.tokens = min(self.max_tokens, self.tokens + refill_count)
            self.last_refill_time = now
    
    def acquire(self, tokens: int = 1, wait: bool = True, max_wait: float = 30.0) -> bool:
        """
        Acquire tokens from the bucket. If not enough tokens are available and wait is True,
        will wait until tokens become available up to max_wait seconds.
        
        Args:
            tokens: Number of tokens to acquire
            wait: Whether to wait for tokens to become available
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if not wait:
                return False
            
            # Calculate wait time and check if it exceeds max_wait
            wait_time = (tokens - self.tokens) * self.refill_interval / self.refill_rate
            if wait_time > max_wait:
                logger.warning(f"Rate limit exceeded. Would need to wait {wait_time:.2f}s, but max wait is {max_wait}s")
                return False
            
            # Wait outside the lock to avoid blocking other threads
        
        logger.info(f"Rate limit hit, waiting {wait_time:.2f}s for more tokens")
        time.sleep(wait_time)
        
        # Try again after waiting
        with self.lock:
            self._refill_tokens()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def execute_with_rate_limit(self, func: Callable, *args, retry_count: int = 3, 
                               backoff_factor: float = 2.0, **kwargs) -> Any:
        """
        Execute a function with rate limiting. If a 429 error is encountered,
        will retry with exponential backoff.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            retry_count: Number of retries on 429 errors
            backoff_factor: Factor to increase wait time between retries
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
        """
        for attempt in range(retry_count + 1):
            # Acquire a token
            if not self.acquire(tokens=1, wait=True):
                raise Exception("Rate limit exceeded and maximum wait time reached")
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                
                # Check if this is a rate limit error (429)
                if "429" in error_str or "Too Many Requests" in error_str:
                    if attempt < retry_count:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"Rate limit (429) hit, retrying in {wait_time:.2f}s (attempt {attempt+1}/{retry_count})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit (429) hit, max retries ({retry_count}) exceeded")
                
                # Re-raise other errors
                raise

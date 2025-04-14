import logging
import time
from threading import Lock
from typing import Dict, Any, Optional, Callable, List, Tuple

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Implements a rate limiter for API calls to prevent 429 Too Many Requests errors.
    Uses a token bucket algorithm to limit request rates with support for multiple
    fallback endpoints.
    """
    
    def __init__(self, max_requests: int = 5, refill_rate: float = 1.0, refill_interval: float = 1.0,
                 fallback_endpoints: Optional[List[str]] = None, endpoint_cooldown: float = 60.0):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of tokens in the bucket (max burst size)
            refill_rate: Number of tokens to add per refill_interval
            refill_interval: Time in seconds between token refills
            fallback_endpoints: List of fallback endpoints to use when primary endpoint is rate limited
            endpoint_cooldown: Time in seconds before retrying a rate-limited endpoint
        """
        self.max_tokens = max_requests
        self.tokens = max_requests
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.last_refill_time = time.time()
        self.lock = Lock()
        
        # Endpoint management
        self.fallback_endpoints = fallback_endpoints or []
        self.endpoint_cooldown = endpoint_cooldown
        self.current_endpoint_index = 0
        self.endpoint_last_errors = {}  # Tracks when each endpoint was last rate limited
    
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
    
    def switch_endpoint(self) -> bool:
        """
        Switch to the next available endpoint that isn't in a cooldown period.
        
        Returns:
            True if successfully switched to a new endpoint, False otherwise
        """
        if not self.fallback_endpoints:
            return False
            
        with self.lock:
            now = time.time()
            
            # Try all possible endpoints
            for _ in range(len(self.fallback_endpoints) + 1):
                # Move to the next endpoint
                self.current_endpoint_index = (self.current_endpoint_index + 1) % (len(self.fallback_endpoints) + 1)
                
                # Get the current endpoint (0 is primary, others are fallbacks)
                current_endpoint = None if self.current_endpoint_index == 0 else self.fallback_endpoints[self.current_endpoint_index - 1]
                
                # Check if this endpoint is in cooldown
                if current_endpoint in self.endpoint_last_errors:
                    cooldown_end = self.endpoint_last_errors[current_endpoint] + self.endpoint_cooldown
                    if now < cooldown_end:
                        cooldown_remaining = cooldown_end - now
                        logger.debug(f"Endpoint {current_endpoint} is in cooldown for {cooldown_remaining:.2f}s more")
                        continue
                
                logger.info(f"Switched to {'primary' if current_endpoint is None else current_endpoint} endpoint")
                return True
                
            # If we get here, all endpoints are in cooldown
            logger.warning("All endpoints are in cooldown, using the least recently failed one")
            
            # Find the endpoint with the oldest error
            oldest_error_time = float('inf')
            oldest_endpoint = None
            
            for endpoint, error_time in self.endpoint_last_errors.items():
                if error_time < oldest_error_time:
                    oldest_error_time = error_time
                    oldest_endpoint = endpoint
            
            # Set the current endpoint to the oldest error endpoint
            if oldest_endpoint is None:
                self.current_endpoint_index = 0
            else:
                for i, endpoint in enumerate(self.fallback_endpoints):
                    if endpoint == oldest_endpoint:
                        self.current_endpoint_index = i + 1
                        break
            
            logger.info(f"Using endpoint with oldest error: {'primary' if self.current_endpoint_index == 0 else self.fallback_endpoints[self.current_endpoint_index - 1]}")
            return True
    
    def mark_endpoint_rate_limited(self) -> None:
        """Mark the current endpoint as rate limited"""
        with self.lock:
            current_endpoint = None if self.current_endpoint_index == 0 else self.fallback_endpoints[self.current_endpoint_index - 1]
            self.endpoint_last_errors[current_endpoint] = time.time()
            logger.warning(f"Marked endpoint {'primary' if current_endpoint is None else current_endpoint} as rate limited")
    
    def get_current_endpoint(self) -> Optional[str]:
        """Get the current endpoint"""
        if self.current_endpoint_index == 0:
            return None  # Primary endpoint
        return self.fallback_endpoints[self.current_endpoint_index - 1]
    
    def execute_with_rate_limit(self, func: Callable, *args, retry_count: int = 3, 
                               backoff_factor: float = 2.0, **kwargs) -> Any:
        """
        Execute a function with rate limiting. If a 429 error is encountered,
        will retry with exponential backoff and endpoint switching.
        
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
                    # Mark the current endpoint as rate limited
                    self.mark_endpoint_rate_limited()
                    
                    # Try to switch to another endpoint
                    if self.switch_endpoint():
                        logger.info(f"Switched endpoint after rate limit error, retrying...")
                        continue
                    
                    # If we can't switch endpoints, use exponential backoff
                    if attempt < retry_count:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"Rate limit (429) hit, retrying in {wait_time:.2f}s (attempt {attempt+1}/{retry_count})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit (429) hit, max retries ({retry_count}) exceeded")
                
                # Re-raise other errors
                raise

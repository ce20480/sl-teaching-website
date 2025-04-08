import logging
import time
from threading import Lock
from web3 import Web3

logger = logging.getLogger(__name__)

class NonceManager:
    """
    Manages nonces for blockchain transactions to prevent nonce-related errors.
    Uses a lock to ensure thread safety when multiple transactions are being sent.
    """
    
    def __init__(self, w3: Web3, address: str):
        self.w3 = w3
        self.address = address
        self.lock = Lock()
        self.current_nonce = None
        self.last_update_time = 0
        self.nonce_cache_ttl = 5  # Seconds to cache nonce before refreshing
    
    def get_next_nonce(self) -> int:
        """
        Get the next available nonce for the address.
        Uses a cached value if it's recent, otherwise fetches from the blockchain.
        """
        with self.lock:
            current_time = time.time()
            
            # If nonce is None or cache has expired, refresh from blockchain
            if self.current_nonce is None or (current_time - self.last_update_time) > self.nonce_cache_ttl:
                try:
                    self.current_nonce = self.w3.eth.get_transaction_count(self.address)
                    self.last_update_time = current_time
                    logger.info(f"Refreshed nonce from blockchain: {self.current_nonce}")
                except Exception as e:
                    if self.current_nonce is not None:
                        logger.warning(f"Failed to refresh nonce, using cached value: {self.current_nonce}. Error: {str(e)}")
                    else:
                        logger.error(f"Failed to get nonce and no cached value available: {str(e)}")
                        raise
            
            # Return and increment the nonce
            next_nonce = self.current_nonce
            self.current_nonce += 1
            return next_nonce
    
    def reset_nonce(self):
        """Force a refresh of the nonce on next get_next_nonce call"""
        with self.lock:
            self.current_nonce = None
            self.last_update_time = 0
    
    def handle_nonce_error(self, error_message: str):
        """
        Handle nonce-related errors by resetting and refreshing the nonce.
        Returns the new nonce to use.
        """
        with self.lock:
            logger.warning(f"Nonce error detected: {error_message}")
            
            # Parse the expected nonce from error message if possible
            try:
                if "minimum expected nonce is" in error_message:
                    import re
                    match = re.search(r"minimum expected nonce is (\d+)", error_message)
                    if match:
                        expected_nonce = int(match.group(1))
                        logger.info(f"Setting nonce to expected value: {expected_nonce}")
                        self.current_nonce = expected_nonce
                        return expected_nonce
            except Exception as e:
                logger.error(f"Error parsing nonce from error message: {str(e)}")
            
            # If parsing failed, just reset and get a fresh nonce
            self.reset_nonce()
            return self.get_next_nonce()

# services/blockchain/transactions.py
from web3.types import TxReceipt
from eth_account.datastructures import SignedTransaction
from ...core.config import settings
from web3 import Web3
from eth_account import Account


class TransactionManager:
    def __init__(self, w3: Web3, account: Account):
        self.w3 = w3
        self.account = account
        self.chain_id = settings.CHAIN_ID
        
    def send_transaction(self, tx_dict: dict) -> TxReceipt:
        # Update with network-specific parameters
        # Filecoin uses 'gas' instead of 'gasPrice'
        tx_dict.update({
            'chainId': self.chain_id,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            # Use maxFeePerGas for EIP-1559 compatible chains
            # 'maxFeePerGas': self.w3.eth.gas_price,
            # For Filecoin, we'll rely on the gas parameter set in the calling code
        })
        
        # Sign the transaction
        signed_tx = self.account.sign_transaction(tx_dict)
        
        # Different versions of web3.py have different attribute names
        # Try both common attribute names for the raw transaction
        if hasattr(signed_tx, 'rawTransaction'):
            raw_tx = signed_tx.rawTransaction
        elif hasattr(signed_tx, 'raw_transaction'):
            raw_tx = signed_tx.raw_transaction
        else:
            # If neither attribute exists, try accessing it as a dictionary
            try:
                raw_tx = signed_tx['rawTransaction']
            except (TypeError, KeyError):
                # Last resort: convert to dict and look for any key that might contain the raw tx
                signed_dict = dict(signed_tx)
                for key in signed_dict:
                    if 'raw' in str(key).lower():
                        raw_tx = signed_dict[key]
                        break
                else:
                    raise ValueError(f"Cannot find raw transaction in {signed_tx}")
        
        # Send the raw transaction
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)
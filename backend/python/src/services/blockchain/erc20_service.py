from web3 import Web3
from web3.contract import Contract
from ...core.config import settings

class ERC20Service:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.FILECOIN_TESTNET_RPC_URL))
        self.account = self.w3.eth.account.from_key(settings.BLOCKCHAIN_PRIVATE_KEY)

    async def mint_tokens(
        self, 
        contract_address: str,
        recipient: str,
        amount: int
    ) -> str:
        """
        Mints ERC20 tokens to a recipient address
        """
        contract = self._load_contract(contract_address)
        tx = contract.functions.mint(
            Web3.to_checksum_address(recipient),
            amount
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address)
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash

    def _load_contract(self, address: str) -> Contract:
        """
        Loads ERC20 contract using standard ABI
        """
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=self._get_erc20_abi()
        )

    def _get_erc20_abi(self) -> list:
        """
        Returns standard ERC20 ABI
        """
        return [
            {
                "constant": False,
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"}
                ],
                "name": "mint",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]

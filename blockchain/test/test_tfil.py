from web3 import Web3

# Connect to Calibration RPC
w3 = Web3(Web3.HTTPProvider("https://api.calibration.node.glif.io/rpc/v1"))

# Your transaction hash
tx_hash = "0x86433f7b5254103758dc4b173161476941cdd9987d826d7a8b671310970f35b6"

# 1. Get the transaction receipt
receipt = w3.eth.get_transaction_receipt(tx_hash)
print(receipt)

# 2. Print out the key details
print("✅ Transaction found!")
print(f"Block Number: {receipt.blockNumber}")
print(f"Status: {'Success ✅' if receipt.status == 1 else 'Failed ❌'}")
print(f"Gas Used: {receipt.gasUsed}")
print(f"Contract Address (if created): {receipt.contractAddress}")
print(f"Logs: {receipt.logs}")

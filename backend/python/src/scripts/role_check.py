from web3 import Web3

# Connect to Filecoin Calibration testnet
w3 = Web3(Web3.HTTPProvider("https://api.calibration.node.glif.io/rpc/v1"))

# Set up
contract_address = "0xB65A3b71b5856a70Fd55E5926d4a22931Bd048D5"
deployer_address = "0x54F26e68C2c60cb81BE26b45D013153d769a2565"

# Load the contract ABI (just the hasRole function is enough)
abi = [{
    "inputs": [
        {"internalType": "bytes32", "name": "role", "type": "bytes32"},
        {"internalType": "address", "name": "account", "type": "address"}
    ],
    "name": "hasRole",
    "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
    "stateMutability": "view",
    "type": "function"
}]

# Instantiate contract
contract = w3.eth.contract(address=contract_address, abi=abi)

# Define role hashes
MINTER_ROLE = Web3.keccak(text="MINTER_ROLE")
DEFAULT_ADMIN_ROLE = b"\x00" * 32  # 0x00...00

# Check permissions
has_minter = contract.functions.hasRole(MINTER_ROLE, deployer_address).call()
has_admin = contract.functions.hasRole(DEFAULT_ADMIN_ROLE, deployer_address).call()

print(f"✅ {deployer_address} has MINTER_ROLE:", has_minter)
print(f"✅ {deployer_address} has DEFAULT_ADMIN_ROLE:", has_admin)

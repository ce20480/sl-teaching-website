from web3 import Web3
from dotenv import load_dotenv
import os
import json

# Load the environment variables from the .env file.
load_dotenv()

def get_abi(path_to_abi):
    """
    Opens and loads a JSON file containing a contract's ABI.
    If the JSON is a dict and has an 'abi' key, returns the ABI list;
    otherwise, assumes the JSON itself is the ABI list.
    """
    with open(path_to_abi, 'r') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'abi' in data:
        return data['abi']
    return data

# Determine the base directory relative to this script.
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Construct the full path to the ABI JSON file for the ASLExperienceToken.
path_to_xp_abi = os.path.join(base_dir, 'contracts', 'ASLExperienceToken.json')
abi = get_abi(path_to_xp_abi)

# Define the valid activity types based on the Solidity enum:
# 0: LESSON_COMPLETION, 1: DATASET_CONTRIBUTION, 2: DAILY_PRACTICE,
# 3: QUIZ_COMPLETION, 4: ACHIEVEMENT_EARNED
VALID_ACTIVITY_TYPES = {
    0: "LESSON_COMPLETION",
    1: "DATASET_CONTRIBUTION",
    2: "DAILY_PRACTICE",
    3: "QUIZ_COMPLETION",
    4: "ACHIEVEMENT_EARNED"
}

# Set the activity type – for example, 1 corresponds to DATASET_CONTRIBUTION.
activity_type = 1
# Validate that the provided activity type exists in our defined enum.
if int(activity_type) not in VALID_ACTIVITY_TYPES:
    print(f"Invalid activity type: {activity_type}. Valid values are: {list(VALID_ACTIVITY_TYPES.keys())}")
    exit(1)
else:
    print(f"Activity type {activity_type} selected: {VALID_ACTIVITY_TYPES[int(activity_type)]}")

# Load key addresses and keys from environment variables.
# 'DEPLOYER_ADDRESS' is the sender account address.
deployer_address = os.environ.get('DEPLOYER_ADDRESS')
# 'TFIL_XP_TOKEN_CONTRACT_ADDRESS' is the deployed contract's address.
contract_address = os.environ.get('TFIL_XP_TOKEN_CONTRACT_ADDRESS')
# 'WEB3_PRIVATE_KEY' must contain the deployer's private key.
private_key = os.environ.get('WEB3_PRIVATE_KEY')

# Create a Web3 instance using the Filecoin testnet RPC URL.
w3 = Web3(Web3.HTTPProvider(os.environ.get('FILECOIN_TESTNET_RPC_URL')))

# Create a contract instance using the contract address and ABI.
contracts = w3.eth.contract(address=contract_address, abi=abi)

# Get the current transaction count (nonce) for the deployer.
nonce = w3.eth.get_transaction_count(deployer_address)

# Convert the deployer address into its checksummed version (for consistency).
checksummed_deployer = Web3.to_checksum_address(deployer_address)

# Retrieve the current gas price in wei.
gas_price = w3.eth.gas_price

# Set the recipient address to the deployer address for now but update later
recipient_address = checksummed_deployer

# Try to estimate the gas required for the awardXP call:
try:
    # Prepare the function call; note that the first parameter (recipient) is set to the deployer.
    # (Change this if you want to mint tokens to a different recipient.)
    func = contracts.functions.awardXP(recipient_address, int(activity_type))
    # Estimate the gas using the deployer_address as 'from'.
    estimated_gas = func.estimate_gas({'from': deployer_address})
    # Add a 20% buffer to the estimate to lower the risk of an out-of-gas error.
    gas_limit = int(estimated_gas * 1.2)
    print(f"Estimated gas: {estimated_gas}, using gas limit: {gas_limit}")
except Exception as e:
    print(f"Failed to estimate gas: {str(e)}. Using default gas limit.")
    gas_limit = 300000  # Fallback gas limit in case estimation fails

# Build the transaction data using the contract's function interface.
# Here, we call the 'awardXP' function with the recipient being the deployer.
# If you want the tokens to be minted to a different account, replace checksummed_deployer with that address.
func = contracts.functions.awardXP(recipient_address, int(activity_type))
tx_data = func.build_transaction({
    'chainId': w3.eth.chain_id,           # Ensures the transaction is valid for the current network.
    'gas': gas_limit,                     # Use the estimated gas limit with buffer.
    'maxFeePerGas': w3.to_wei('2', 'gwei'),  # Set maximum fee per gas.
    'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),  # Set maximum priority fee.
    'nonce': nonce,                       # Use the current nonce for the deployer.
})

# Sign the transaction with the deployer's private key.
# Make sure 'private_key' is the actual private key, not just the address.
signed_tx = w3.eth.account.sign_transaction(tx_data, private_key=private_key)

# Send the signed transaction to the network and capture the transaction hash.
transaction_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
print(f"Transaction sent with hash: {transaction_hash}")

# Wait for the transaction receipt (this confirms whether the transaction was mined and executed).
try:
    receipt = w3.eth.wait_for_transaction_receipt(transaction_hash, timeout=120)
    print("Transaction Receipt:")
    print(receipt)
    
    if receipt.status != 1:
        print("Transaction reverted!")
    else:
        print("Transaction confirmed successfully!")
except Exception as e:
    print(f"Error fetching transaction receipt: {str(e)}")

# Check the token balance of the recipient (deployer_address in this example) by calling balanceOf.
try:
    balance = contracts.functions.balanceOf(recipient_address).call()
    print(f"Token balance for {recipient_address}: {balance}")
except Exception as e:
    print(f"Error fetching token balance: {str(e)}")

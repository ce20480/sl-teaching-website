#!/usr/bin/env python3
"""
Simplified contract deployment script for ASL Teaching Project.
Direct conversion of the TypeScript version.
"""
import os
import json
import logging
from pathlib import Path
from web3 import Web3
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to Python path for imports
import sys
path_to_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
path_to_src = os.path.join(path_to_root, "src")
sys.path.append(path_to_src)

from core.config import settings

# Default path for contracts
CONTRACT_PATH = os.path.join(path_to_src, "core", "contracts", "s-contracts", "abis")

def load_contract_data(contract_name):
    """Load contract ABI and bytecode from file"""
    file_path = os.path.join(CONTRACT_PATH, f"{contract_name}.json")
    with open(file_path, 'r') as f:
        contract_json = json.load(f)
    
    # Handle different JSON formats
    if isinstance(contract_json, dict):
        if 'abi' in contract_json:
            abi = contract_json['abi']
        else:
            abi = contract_json
            
        if 'bytecode' in contract_json:
            bytecode = contract_json['bytecode']
        elif 'object' in contract_json:
            bytecode = contract_json['object']
        else:
            bytecode = ''
    else:
        abi = contract_json
        bytecode = ''
    
    return abi, bytecode

async def main():
    # Connect to provider
    provider_url = settings.WEB3_PROVIDER_URL
    private_key = settings.BLOCKCHAIN_PRIVATE_KEY
    
    print("Getting deployer account...")
    w3 = Web3(Web3.HTTPProvider(provider_url))
    
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to provider at {provider_url}")
    
    # Create account from private key
    account = w3.eth.account.from_key(private_key)
    print(f"Deploying contracts with account: {account.address}")
    
    # Deploy Achievement Token
    print("Deploying AchievementToken contract...")
    achievement_abi, achievement_bytecode = load_contract_data("AchievementToken")
    achievement_contract = w3.eth.contract(abi=achievement_abi, bytecode=achievement_bytecode)
    
    # Get nonce for the account
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Deploy the contract
    # Similar to TypeScript's AchievementToken.deploy()
    deploy_tx = achievement_contract.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 5000000,  # Gas limit
        'gasPrice': w3.eth.gas_price,
    })
    
    # Sign transaction
    signed_tx = account.sign_transaction(deploy_tx)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
    achievement_address = tx_receipt.contractAddress
    print(f"AchievementToken deployed to: {achievement_address}")
    print("Achievement contract confirmed on network")
    
    # Deploy XP Token
    print("Deploying XP Token contract...")
    xp_abi, xp_bytecode = load_contract_data("ASLExperienceToken")
    xp_contract = w3.eth.contract(abi=xp_abi, bytecode=xp_bytecode)
    
    # Update nonce for next transaction
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Deploy XP contract
    deploy_tx = xp_contract.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 5000000,
        'gasPrice': w3.eth.gas_price,
    })
    
    signed_tx = account.sign_transaction(deploy_tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
    xp_address = tx_receipt.contractAddress
    print(f"XP Token deployed to: {xp_address}")
    
    # Set up permissions between contracts
    print("Setting up contract permissions...")
    # Create contract instance with deployed address
    xp_instance = w3.eth.contract(address=xp_address, abi=xp_abi)
    
    # Get MINTER_ROLE value (assuming it's a public constant)
    minter_role = xp_instance.functions.MINTER_ROLE().call()
    
    # Update nonce
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Grant minter role to achievement contract
    grant_tx = xp_instance.functions.grantRole(
        minter_role,
        achievement_address
    ).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
    })
    
    signed_tx = account.sign_transaction(grant_tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    
    print("Deployment complete!")
    
    # Save contract addresses to config
    env_file = os.path.join(path_to_root, ".env")
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        lines = env_content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('ERC20_XP_CONTRACT_ADDRESS='):
                updated_lines.append(f'ERC20_XP_CONTRACT_ADDRESS={xp_address}')
            elif line.startswith('TFIL_ACHIEVEMENT_CONTRACT_ADDRESS='):
                updated_lines.append(f'TFIL_ACHIEVEMENT_CONTRACT_ADDRESS={achievement_address}')
            else:
                updated_lines.append(line)
        
        with open(env_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print("Updated .env file with contract addresses")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
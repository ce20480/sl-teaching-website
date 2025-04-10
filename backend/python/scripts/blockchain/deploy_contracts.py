#!/usr/bin/env python3
"""
Contract deployment script for ASL Teaching Project.

This script deploys the XP Token and Achievement NFT contracts to the specified
blockchain network and saves the deployment information.
"""
import os
import json
import logging
from pathlib import Path
import argparse
from web3 import Web3

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import sys
path_to_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
path_to_src = os.path.join(path_to_root, "src")
sys.path.append(path_to_src)

from core.config import settings

# Default paths
DEFAULT_ABI_DIR = os.path.join(path_to_src, "core", "contracts", "s-contracts", "abis")
DEFAULT_OUTPUT_DIR = os.path.join(path_to_root, "deployments")

def load_contract_abi(file_path):
    """Load contract ABI from JSON file"""
    try:
        with open(file_path, 'r') as f:
            contract_json = json.load(f)
        logger.info(f"Loaded ABI: {contract_json}")
        if isinstance(contract_json, dict) and 'abi' in contract_json:  
            logger.info(f"Loaded ABI: {contract_json['abi']}")
            return contract_json['abi']
        return contract_json  # Assume the JSON itself is the ABI list
    except Exception as e:
        logger.error(f"Error loading ABI from {file_path}: {e}")
        raise

def load_contract_bytecode(file_path):
    """Load contract bytecode from file"""
    try:
        with open(file_path, 'r') as f:
            bytecode = f.read().strip()
            # If bytecode is stored as JSON
            if bytecode.startswith('{'):
                return json.loads(bytecode)['object']
            return bytecode
    except Exception as e:
        logger.error(f"Error loading bytecode from {file_path}: {e}")
        raise

def connect_web3(provider_url, private_key):
    """Connect to blockchain and return web3 instance and account"""
    try:
        # Connect to provider
        w3 = Web3(Web3.HTTPProvider(provider_url))
        
        # # Add POA middleware for networks like Ethereum testnets
        # w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Check connection
        if not w3.is_connected():
            raise ConnectionError(f"Could not connect to provider at {provider_url}")
        
        # Create account from private key
        account = w3.eth.account.from_key(private_key)
        
        # Log network info
        chain_id = w3.eth.chain_id
        logger.info(f"Connected to network with chain ID: {chain_id}")
        logger.info(f"Account address: {account.address}")
        
        # Check balance
        balance = w3.eth.get_balance(account.address)
        logger.info(f"Account balance: {Web3.from_wei(balance, 'ether')} ETH")
        
        if balance == 0:
            logger.warning("Account has zero balance! Deployment will likely fail.")
        
        return w3, account
    except Exception as e:
        logger.error(f"Error connecting to blockchain: {e}")
        raise

def deploy_contract(w3, account, contract_name, abi, bytecode, constructor_args=None):
    """Deploy a contract and return the deployed contract instance"""
    try:
        logger.info(f"Deploying {contract_name}...")
        
        # Prepare contract
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Prepare constructor arguments
        if constructor_args is None:
            constructor_args = []
        
        # Estimate gas
        try:
            gas_estimate = contract.constructor(*constructor_args).estimate_gas() * 1.2 
        except Exception as e:
            logger.error(f"Error estimating gas for {contract_name}: {e}")
            raise
        
        # Get nonce
        nonce = w3.eth.get_transaction_count(account.address)
        
        # Get gas price with EIP-1559 support
        tx_params = {
            'from': account.address,
            'nonce': nonce,
            'gas': gas_estimate,
        }
        
        # Check if network supports EIP-1559
        latest_block = w3.eth.get_block('latest')
        if 'baseFeePerGas' in latest_block:
            # EIP-1559 transaction
            base_fee = latest_block['baseFeePerGas']
            priority_fee = w3.to_wei('1', 'gwei')
            max_fee = base_fee * 2 + priority_fee
            
            tx_params['maxFeePerGas'] = max_fee
            tx_params['maxPriorityFeePerGas'] = priority_fee
            
            logger.info(f"Using EIP-1559 fees: base_fee={Web3.from_wei(base_fee, 'gwei')} gwei, "
                      f"priority_fee={Web3.from_wei(priority_fee, 'gwei')} gwei, "
                      f"max_fee={Web3.from_wei(max_fee, 'gwei')} gwei")
        else:
            # Legacy transaction
            gas_price = w3.eth.gas_price
            tx_params['gasPrice'] = gas_price
            logger.info(f"Using legacy gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build and sign transaction
        contract_txn = contract.constructor(*constructor_args).build_transaction(tx_params)
        signed_txn = account.sign_transaction(contract_txn)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(f"Transaction sent: {tx_hash.hex()}")
        
        # Wait for receipt
        logger.info("Waiting for transaction to be mined...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        contract_address = tx_receipt.contractAddress
        
        logger.info(f"{contract_name} deployed to: {contract_address}")
        logger.info(f"Gas used: {tx_receipt.gasUsed}")
        
        # Return deployed contract
        return w3.eth.contract(address=contract_address, abi=abi), tx_receipt
    except Exception as e:
        logger.error(f"Error deploying {contract_name}: {e}")
        raise

def save_deployment_info(output_dir, network_id, contract_name, address, abi, tx_hash):
    """Save deployment information to file"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create network directory if it doesn't exist
        network_dir = output_dir / str(network_id)
        os.makedirs(network_dir, exist_ok=True)
        
        # Save deployment info
        deployment_info = {
            'contract_name': contract_name,
            'address': address,
            'abi': abi,
            'transaction_hash': tx_hash,
            'timestamp': int(time.time())
        }
        
        # Write to file
        output_file = network_dir / f"{contract_name.lower()}.json"
        with open(output_file, 'w') as f:
            json.dump(deployment_info, f, indent=2)
            
        logger.info(f"Deployment info saved to: {output_file}")
    except Exception as e:
        logger.error(f"Error saving deployment info: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Deploy contracts for ASL Teaching Project')
    parser.add_argument('--network', type=str, default='testnet', 
                        help='Network to deploy to (local, testnet, or mainnet)')
    parser.add_argument('--private-key', type=str, 
                        help='Private key for deployment account')
    parser.add_argument('--provider-url', type=str, 
                        help='Provider URL for blockchain connection')
    parser.add_argument('--abi-dir', type=str, default=str(DEFAULT_ABI_DIR),
                        help='Directory containing contract ABIs and bytecode')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help='Directory to save deployment information')
    
    args = parser.parse_args()
    
    # Get configuration based on network
    if args.network == 'local':
        provider_url = args.provider_url or "http://localhost:8545"
        chain_id = 1337
    elif args.network == 'testnet':
        provider_url = args.provider_url or settings.FILECOIN_TESTNET_RPC_URL
        chain_id = 314159  # Filecoin Calibration testnet
    elif args.network == 'mainnet':
        provider_url = args.provider_url or "https://api.node.glif.io/rpc/v1"
        chain_id = 314  # Filecoin mainnet
    else:
        logger.error(f"Unknown network: {args.network}")
        return
    
    # Get private key
    private_key = args.private_key or settings.BLOCKCHAIN_PRIVATE_KEY
    if not private_key:
        logger.error("No private key provided. Use --private-key or set BLOCKCHAIN_PRIVATE_KEY in .env")
        return
    
    # Convert path arguments to Path objects
    abi_dir = Path(args.abi_dir)
    output_dir = Path(args.output_dir)
    
    try:
        # Connect to blockchain
        w3, account = connect_web3(provider_url, private_key)
        
        # Load XP Token contract artifacts
        xp_abi = load_contract_abi(abi_dir / "ASLExperienceToken.json")
        xp_bytecode = load_contract_bytecode(abi_dir / "ASLExperienceToken.json")
        
        # Deploy XP Token contract
        xp_contract, xp_receipt = deploy_contract(
            w3, account, "ASLExperienceToken", xp_abi, xp_bytecode,
            constructor_args=[
                "ASL Teaching XP",  # Name
                "ASLXP",            # Symbol
                account.address     # Owner address
            ]
        )
        
        # Save XP Token deployment info
        save_deployment_info(
            output_dir, chain_id, "ASLExperienceToken", 
            xp_contract.address, xp_abi, xp_receipt.transactionHash.hex()
        )
        
        # Load Achievement NFT contract artifacts
        achievement_abi = load_contract_abi(abi_dir / "AchievementToken.json")
        achievement_bytecode = load_contract_bytecode(abi_dir / "AchievementToken.json")
        
        # Deploy Achievement NFT contract
        achievement_contract, achievement_receipt = deploy_contract(
            w3, account, "AchievementToken", achievement_abi, achievement_bytecode,
            constructor_args=[
                "ASL Teaching Achievements",  # Name
                "ASLACH",                     # Symbol
                "https://asl-teaching.com/api/metadata/",  # Base URI
                xp_contract.address,          # XP Token address
                account.address               # Owner address
            ]
        )
        
        # Save Achievement NFT deployment info
        save_deployment_info(
            output_dir, chain_id, "AchievementToken", 
            achievement_contract.address, achievement_abi, 
            achievement_receipt.transactionHash.hex()
        )
        
        # Print deployment summary
        logger.info("\n=== Deployment Summary ===")
        logger.info(f"Network: {args.network} (Chain ID: {chain_id})")
        logger.info(f"XP Token: {xp_contract.address}")
        logger.info(f"Achievement NFT: {achievement_contract.address}")
        logger.info(f"Deployment account: {account.address}")
        logger.info(f"Deployment files saved to: {output_dir / str(chain_id)}")
        
        # Update .env file with deployment addresses
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            # Read current .env file
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            # Update contract addresses
            env_lines = env_content.split('\n')
            updated_lines = []
            
            xp_updated = False
            achievement_updated = False
            
            for line in env_lines:
                if line.startswith('ERC20_XP_CONTRACT_ADDRESS='):
                    updated_lines.append(f'ERC20_XP_CONTRACT_ADDRESS={xp_contract.address}')
                    xp_updated = True
                elif line.startswith('TFIL_ACHIEVEMENT_CONTRACT_ADDRESS='):
                    updated_lines.append(f'TFIL_ACHIEVEMENT_CONTRACT_ADDRESS={achievement_contract.address}')
                    achievement_updated = True
                else:
                    updated_lines.append(line)
            
            # Add addresses if not updated
            if not xp_updated:
                updated_lines.append(f'ERC20_XP_CONTRACT_ADDRESS={xp_contract.address}')
            if not achievement_updated:
                updated_lines.append(f'TFIL_ACHIEVEMENT_CONTRACT_ADDRESS={achievement_contract.address}')
            
            # Write updated .env file
            with open(env_file, 'w') as f:
                f.write('\n'.join(updated_lines))
            
            logger.info(f"Updated .env file with deployment addresses")
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        
if __name__ == "__main__":
    import time
    main() 
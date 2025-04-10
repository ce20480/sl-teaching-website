## Contract Deployment

Before running the backend, you need to deploy the smart contracts to the blockchain:

1. Make sure your environment is set up correctly (see Environment Setup section)

2. Run the deployment script:

   ```
   # Deploy to local development network
   python scripts/blockchain/deploy_contracts.py --network local

   # Deploy to testnet (requires private key with funds)
   python scripts/blockchain/deploy_contracts.py --network testnet

   # Deploy with custom private key
   python scripts/blockchain/deploy_contracts.py --network testnet --private-key YOUR_PRIVATE_KEY
   ```

3. The script will:

   - Deploy the XP Token contract
   - Deploy the Achievement NFT contract
   - Save deployment information to `src/deployments/{chain_id}/`
   - Update your `.env` file with the contract addresses

4. Start the backend with the deployed contract addresses

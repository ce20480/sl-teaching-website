# Blockchain Services

This directory contains services for interacting with blockchain contracts, including transaction management and reward services.

## Overview

The blockchain services provide a standardized way to interact with smart contracts on the Filecoin blockchain. The system supports both testnet and local environments, with environment selection controlled via the `BLOCKCHAIN_ENV` setting in the `.env` file.

## Core Components

### BaseContractService

The `BaseContractService` is a base class that provides common functionality for blockchain interactions, including:

- Transaction simulation
- EIP-1559 fee calculation
- Enhanced error handling
- Transaction tracking

All contract-specific services should inherit from this base class to ensure consistent transaction handling and error management.

### TransactionManager

The `TransactionManager` handles the sending and tracking of blockchain transactions. It includes:

- Enhanced transaction handling with improved error management and logging
- Integration of EIP-1559 fee calculations and transaction simulation
- Improved methods for sending transactions and checking their status

## Reward Services

### XP Reward Service

The XP reward service (`XpRewardServiceV2`) handles the awarding of XP tokens to users. It inherits from the `BaseContractService` and provides methods for:

- Awarding XP based on activity type
- Awarding custom amounts of XP
- Updating reward rates
- Checking token balances

### Achievement Reward Service

The Achievement reward service (`AchievementRewardServiceV2`) handles the minting of achievement NFTs for users. It inherits from the `BaseContractService` and provides methods for:

- Minting achievement NFTs
- Updating NFT metadata
- Getting user achievements
- Awarding achievements based on XP amount

## API Endpoints

The V2 reward services are exposed through the `/api/rewards/v2` endpoints:

### XP Endpoints

- `POST /api/rewards/v2/xp/award/{address}` - Award XP based on activity type
- `POST /api/rewards/v2/xp/award-custom/{address}` - Award a custom amount of XP
- `POST /api/rewards/v2/xp/update-reward-rate` - Update the reward rate for an activity type
- `GET /api/rewards/v2/xp/balance/{address}` - Get the current XP token balance for an address
- `GET /api/rewards/v2/transactions/{tx_hash}` - Get the status of a specific transaction

### Achievement Endpoints

- `POST /api/rewards/v2/achievements/mint/{address}` - Mint a new achievement token
- `POST /api/rewards/v2/achievements/update-metadata/{token_id}` - Update the IPFS hash for a token's metadata
- `GET /api/rewards/v2/achievements/user/{address}` - Get all achievements for a user
- `GET /api/rewards/v2/achievements/{token_id}` - Get achievement details for a specific token
- `POST /api/rewards/v2/achievements/award-by-xp/{address}` - Award achievement based on total XP

## Environment Configuration

The system supports multiple blockchain environments:

1. **Testnet environment** (Filecoin Calibration testnet)
   - RPC URL: https://api.calibration.node.glif.io/rpc/v1
   - Contract: ASLExperienceToken deployed on testnet

2. **Local environment** (Local Filecoin node)
   - RPC URL: http://127.0.0.1:1234/rpc/v1
   - Requires deploying contract to local node

Environment selection is controlled via the `BLOCKCHAIN_ENV` setting in the `.env` file.

## Testing

A test script is provided at `/backend/python/src/tests/test_reward_services_v2.py` to verify that the V2 services are functioning correctly. To run the tests:

```bash
cd /backend/python/src
python -m tests.test_reward_services_v2
```

Make sure to update the test address in the script to a valid address that you control before running the tests.

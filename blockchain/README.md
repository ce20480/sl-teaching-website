# Blockchain (Hardhat) Setup Guide

This guide explains how to set up the blockchain development environment using Hardhat, compile contracts, run tests, and deploy them locally or to a testnet.

## Prerequisites

Before you begin, ensure you have the following installed:

- Node.js (LTS version recommended)
- npm (comes with Node.js)

## Installation

1.  **Navigate to the blockchain directory:**
    From the project root, navigate to the blockchain directory:

    ```bash
    cd blockchain
    ```

2.  **Install dependencies:**
    Run the following command to install the necessary Node modules, including Hardhat and its plugins:
    ```bash
    npm install
    ```

## Environment Variables

The Hardhat environment requires private keys for deploying contracts and an optional API key for contract verification on block explorers.

1.  **Create a `.env` file:**
    In the `blockchain` directory, copy the example environment file:

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the newly created `.env` file and add your deployer private key and optional block explorer API key.

    - `WEB3_PRIVATE_KEY`: **Essential.** The private key of the account that will pay for gas to deploy the contracts. Ensure it has funds on the target network.
    - `ETHERSCAN_API_KEY`: **Optional.** Used for automatic source code verification on services like Etherscan or Filscan.

    **Important:** Keep your `WEB3_PRIVATE_KEY` secure and never commit it to version control.

## Compiling Contracts

To compile the Solidity smart contracts located in the `contracts/` directory:

```bash
npm run compile
# or
hardhat compile
```

This command generates artifacts (ABI, bytecode) in the `artifacts/` directory and TypeScript typings in `typechain-types/` (based on `hardhat.config.ts`).

## Running Tests

To run the automated tests located in the `test/` directory:

```bash
npm test
# or
hardhat test
```

Tests are run against a temporary local Hardhat Network by default.

## Deploying Contracts

The project includes scripts in the `scripts/` directory for deployment.

1.  **Deployment Script:** Review the `scripts/deploy.ts` script to understand which contracts are deployed.

2.  **Configure Network:** Ensure the desired network (e.g., `filecoinTestnet`) is configured in `hardhat.config.ts` and your `.env` file has the correct `WEB3_PRIVATE_KEY` with funds for that network.

3.  **Run Deployment:**

    ```bash
    # Example: Deploy to Filecoin Calibration Testnet
    npm run deploy:testnet
    # or
    # hardhat run scripts/deploy.ts --network filecoinTestnet
    ```

4.  **Record Addresses:** After successful deployment, the script should output the addresses of the deployed contracts. **Crucially, update your `.env` files (in `backend/python` and `frontend`) with these new addresses.** You might also want to add them as comments to your `blockchain/.env.example` or `.env` for future reference.

## Utility Scripts

- **`npm run generate-types`**: Manually regenerate TypeChain typings.
- **`npm run extract-abis`**: Extract ABIs from artifacts (useful for frontend/backend integration).
- **`npm run prepare-deploy`**: Convenience script to compile, extract ABIs, and generate types.

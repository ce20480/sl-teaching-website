# Frontend Setup Guide

This guide explains how to set up and run the frontend of the ASL Teaching Website locally.

## Prerequisites

Before you begin, ensure you have the following installed:

- Node.js (LTS version recommended)
- npm (comes with Node.js)

## Installation

1.  **Clone the repository:**
    If you haven't already, clone the main project repository to your local machine.

2.  **Navigate to the frontend directory:**

    ```bash
    cd path/to/your/project/frontend
    ```

3.  **Install dependencies:**
    Run the following command to install the necessary Node modules:
    ```bash
    npm install
    ```

## Environment Variables

The frontend requires certain environment variables to connect to backend services and blockchain components.

1.  **Create a `.env` file:**
    In the `frontend` directory, copy the example environment file:

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the newly created `.env` file and replace the placeholder values with your actual configuration details.

    - `VITE_WALLET_CONNECT_PROJECT_ID`: Necessary for connecting user wallets via WalletConnect. Get this from [WalletConnect Cloud](https://cloud.walletconnect.com/).
    - `VITE_WALLET_FILECOIN_TESTNET`: The address for interacting with Filecoin storage (ensure this matches the network your backend/blockchain uses).
    - `VITE_CONTRACT_ADDRESS`: Points to the deployed main smart contract (obtain this after deploying the blockchain contracts).
    - `VITE_XP_TOKEN_CONTRACT_ADDRESS`: Points to the deployed ERC20 token contract (obtain this after deploying the blockchain contracts).

    **Important:** Only variables prefixed with `VITE_` are exposed to the browser. Do not store sensitive secrets in this file.

## Running the Development Server

Once you have installed the dependencies and configured your `.env` file, you can start the local development server:

```bash
npm run dev
```

This command will:

- Start the Vite development server.
- Typically, the frontend will be accessible at `http://localhost:5173` or `http://localhost:5174` (check the terminal output for the exact URL).
- Enable Hot Module Replacement (HMR) for a faster development experience.

**API Proxy:** The development server is configured to proxy requests starting with `/api` to `http://localhost:4000`. This means your Express middleware server should be running on port 4000 for the frontend to communicate with it correctly during development.

## Building for Production

To create an optimized build for deployment:

```bash
npm run build
```

This will generate static assets in the `dist` directory.

## Linting

To check the code for potential errors and style issues:

```bash
npm run lint
```

## Overview

React-based frontend for ASL teaching platform with real-time sign language detection and storage capabilities.

## Development

- Frontend runs on port 5173 or 5174 (Vite default)
- Configuration in `src/config.ts` for API endpoints
- Uses shadcn/ui for components
- Implements file upload with preview functionality

## Key Features

- Real-time sign language detection interface
- File upload with preview
- Connection to Express middleware server
- Filecoin storage integration

## Common Issues

1. CORS errors when connecting directly to Python backend
   - Always route through Express middleware (port 3000)
2. File upload size limits
   - Configure in both frontend and backend
3. Environment variables
   - Check `.env` for API endpoints

## Project Structure

```
src/
├── components/
│   ├── features/    # Feature-specific components
│   └── ui/         # Reusable UI components
├── services/
│   └── api/        # API integration
└── pages/          # Route components
```

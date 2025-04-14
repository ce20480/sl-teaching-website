# ASL Teaching Website (SignLang)

SignLang: Empowering Accessibility through Open-Source and Decentralization

Every day, millions rely on sign language to communicate—but access to high-quality sign language translation remains limited, expensive, and monopolized by big tech. Current solutions are often inaccessible due to high costs, limited availability, and proprietary restrictions, creating significant barriers in critical areas such as healthcare, education, and everyday interactions.

SignLang is here to disrupt this. We're building an open-source, decentralized American Sign Language (ASL) translator, leveraging the power of the Filecoin ecosystem and its decentralized storage (Akave, Storacha, Lighthouse, Recall) and compute services (Lilypad).

## The Problem We're Solving:

- **Educational Barriers:** Many educational institutions lack affordable, reliable ASL translation resources, limiting opportunities for Deaf and hard-of-hearing students.
- **Healthcare Communication:** Miscommunication in healthcare settings due to limited interpreter availability can lead to severe misunderstandings and reduced quality of care.
- **Accessibility in Daily Life:** Dependence on costly human interpreters or centralized, proprietary translation solutions leaves many users isolated, unable to communicate spontaneously or in real-time.

## Our Vision

We envision a future where sign language translation models aren't gatekept by conglomerates but grown organically by the community itself. The availability of comprehensive training data remains a significant barrier—but we've turned this challenge into our greatest opportunity.

## How it Works:

- **Community-Driven Data Collection:** Our initial app helps users learn and practice ASL. As users improve, they contribute high-quality, user-generated videos back into our dataset, enriching the model organically.
- **Decentralized Storage (Filecoin Network):** We utilize decentralized storage providers like Akave, Storacha, Lighthouse, and Recall. Filecoin's incentivized storage network ensures secure, censorship-resistant, and privacy-focused data hosting.
- **Decentralized Compute with Lilypad:** By leveraging Lilypad's decentralized compute network, SignLang runs translations without reliance on centralized cloud providers—lowering costs and preserving user privacy.
- **Achievement System:** We've implemented an ERC4973 Soulbound Token system to reward users for their contributions and progress in learning ASL. These non-transferable achievement tokens are stored on IPFS and provide a permanent record of a user's journey in learning ASL.

## Tech Stack Overview

- **Frontend:** React, TypeScript, Vite, TailwindCSS, Shadcn UI, Web3Modal/Wagmi
- **Backend (Middleware):** Express, TypeScript
- **Backend (Core):** Python, FastAPI, OpenCV, ML Models
- **Blockchain:** Solidity, Hardhat, OpenZeppelin, Filecoin FVM/EVM, IPFS
- **Decentralized Services:** Filecoin Storage (Akave, Storacha, Lighthouse), Lilypad Compute

## Project Structure and Local Setup Guide

This project is structured as a monorepo containing distinct parts: frontend, backend (Python core and Express middleware), and blockchain components.

To run the entire application stack locally, you will need to set up and run each component individually. Please refer to the specific README file within each directory for detailed installation, configuration (including `.env` setup), and running instructions.

1.  **Frontend (`./frontend`)**

    - Handles the user interface and interaction.
    - Communicates with the Express middleware.
    - **Setup Guide:** [`frontend/README.md`](./frontend/README.md)
    - _Default Port (Development):_ `5173` or `5174`

2.  **Backend - Express Middleware (`./backend/express`)**

    - Acts as a proxy between the frontend and the Python backend.
    - Handles CORS, rate limiting, and potentially some request/response formatting.
    - **Setup Guide:** [`backend/express/README.md`](./backend/express/README.md)
    - _Default Port (Development):_ `4000`

3.  **Backend - Python Core (`./backend/python`)**

    - Contains the main application logic, including ML model execution, data processing, and blockchain interactions.
    - Exposes a FastAPI interface.
    - **Setup Guide:** [`backend/python/README.md`](./backend/python/README.md)
    - _Default Port (Development):_ `8000`

4.  **Blockchain (`./blockchain`)**
    - Contains the Solidity smart contracts (ERC4973 Achievement Token, XP Token).
    - Uses Hardhat for development, testing, and deployment.
    - **Setup Guide:** [`blockchain/README.md`](./blockchain/README.md)

**Interaction Flow (Local Development):**

`User Browser (Frontend @ :5173)` -> `Express Middleware (@ :4000)` -> `Python Backend (@ :8000)`

The Python backend and potentially the frontend interact directly with the deployed blockchain contracts based on their respective `.env` configurations.

## Getting Started

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/ce20480/asl-teaching-website.git
    cd asl-teaching-website
    ```

2.  **Follow the setup guides:** Navigate into each directory (`frontend`, `backend/express`, `backend/python`, `blockchain`) and follow the instructions in their respective `README.md` files to install dependencies, set up environment variables (`.env`), and run each service.

## Contribution

Contributions are welcome! Please refer to the contribution guidelines (if available) or open an issue/pull request.

## License

[Specify your license, e.g., MIT License]

## Features

- 🎥 Real-time ASL translation using camera
- 📚 Interactive ASL lessons with progress tracking
- 🌟 ERC4973 Achievement Token system for learning milestones
- 🤝 Community contribution platform
- 👤 Personal profile with learning statistics
- 💎 Soulbound achievements stored on IPFS
- 🔐 Secure wallet integration with Web3Modal

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- TailwindCSS
- Shadcn UI
- React Router Dom
- Web3Modal & wagmi.js for wallet integration

### Backend

- FastAPI
- Python
- OpenCV for image processing
- Machine Learning models for ASL recognition

### Blockchain

- Solidity 0.8.19
- OpenZeppelin Contracts
- Filecoin FVM
- IPFS for metadata storage

## Prerequisites

Before you begin, ensure you have installed:

- Node.js (v18 or higher)
- Python (v3.8 or higher)
- pip (Python package manager)
- Git
- A Filecoin wallet with FIL for deployment

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/asl-teaching-website.git
cd asl-teaching-website
```

## Running the Application

1. Start the frontend development server:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

2. Starting the backend

### Python

```bash
cd backend/python
poetry install
poetry run uvicorn main:app --reload
```

### Express

```bash
cd backend/express
npm install
npm run dev
```

The Express server will be available at `http://localhost:4000`

The backend API will be available at `http://localhost:8000`

3. Start the Akave server (in a new terminal):

```bash
cd akave
npm install
npm run dev
```

The Akave server will be available at `http://localhost:3000`

### Environment Setup

1. Frontend environment variables (frontend/.env):

```env
REACT_APP_WALLET_CONNECT_PROJECT_ID=your_wallet_connect_project_id
REACT_APP_CONTRACT_ADDRESS=your_deployed_contract_address
```

2. Backend environment variables (backend/.env):

```env
DATABASE_URL=your_database_url
JWT_SECRET=your_jwt_secret
```

3. Akave environment variables (akave/.env):

```env
AKAVE_API_KEY=your_akave_api_key
STORAGE_PATH=your_storage_path
```

4. Express environment variables (express/.env):

```env
PORT=4000
NODE_ENV=development
```

### Verifying All Servers

1. Frontend: Visit `http://localhost:5173` - you should see the main application interface
2. Backend: Visit `http://localhost:8000/docs` - you should see the Swagger API documentation
3. Akave: Visit `http://localhost:3000/health` - you should see a health check response
4. Express: Visit `http://localhost:4000/api/health` - you should see a health check response

### Troubleshooting

If any server fails to start:

1. Check if the required ports are available
2. Verify all environment variables are set correctly
3. Ensure all dependencies are installed
4. Check the server logs for specific error messages

### Configuration Details

#### TailwindCSS Configuration

The `frontend/tailwind.config.js` file should contain:

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./index.html"],
  theme: {
    // Theme configuration including colors, animations, etc.
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        // ... other color configurations
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

#### PostCSS Configuration

The `frontend/postcss.config.js` file should contain:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

#### Vite Configuration

The `frontend/vite.config.ts` file should contain:

```typescript
import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // ... other aliases
    },
  },
  // ... other configurations
});
```

These configurations work together to provide:

- Modern React development with Vite
- Utility-first styling with TailwindCSS
- Proper CSS processing with PostCSS
- Component library support with Shadcn UI

## Development

### Frontend Development

- Run tests: `npm test`
- Build for production: `npm run build`
- Preview production build: `npm run preview`

### Backend Development

- API documentation available at `http://localhost:8000/docs`
- Run tests: `pytest`
- Format code: `black .`

## Build and Generated Files

After cloning the repository, you'll need to generate several files before you can start development:

### Smart Contract Files

1. Compile the contracts to generate artifacts:

```bash
npm run compile
```

2. Generate TypeScript types for contracts:

```bash
npm run generate-types
```

3. Extract ABIs for frontend use:

```bash
npm run extract-abis
```

These commands will create:

- `artifacts/` - Compiled contract artifacts
- `cache/` - Solidity compilation cache
- `typechain-types/` - TypeScript bindings for contracts
- `frontend/src/contracts/types/` - Frontend contract types
- `contracts/*.json` - Contract ABIs

## Project Structure

```
asl-teaching-website/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── WalletConnect.tsx
│   │   │   └── AchievementDisplay.tsx
│   │   ├── pages/
│   │   ├── styles/
│   │   └── main.tsx
│   ├── public/
│   └── package.json
├── contracts/
│   └── AchievementToken.sol
├── scripts/
│   └── deploy.ts
├── backend/
│   ├── app/
│   ├── tests/
│   └── requirements.txt
├── hardhat.config.ts
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/YourFeature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/YourFeature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all contributors who have helped with the development
- Shadcn UI for the component library
- React and FastAPI communities for excellent documentation
- Filecoin Foundation for supporting decentralized storage
- OpenZeppelin for secure smart contract implementations

## Architecture

```
asl-teaching-website/
├── frontend/          # React + Vite frontend
├── backend/
│   ├── express/      # Express middleware server
│   └── python/       # FastAPI + ML backend
└── docs/             # Additional documentation
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Poetry
- Docker Desktop
- Akave API credentials

### Environment Setup

1. Clone repository:

```bash
git clone https://github.com/yourusername/asl-teaching-website.git
cd asl-teaching-website
```

2. Configure environment:

```bash
# Backend Python
cd backend/python
cp .env.example .env
# Edit .env with your Akave credentials

# Frontend
cd ../../frontend
cp .env.example .env
```

### Starting Services

1. Start Akave Storage (required for file operations):

```bash
cd backend/python
poetry run akave start
```

2. Start Python Backend:

```bash
cd backend/python
poetry install
poetry run dev
```

3. Start Express Middleware:

```bash
cd backend/express
npm install
npm run dev
```

4. Start Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Service Architecture

| Service    | Port | Description                  |
| ---------- | ---- | ---------------------------- |
| Frontend   | 5173 | Vite + React UI              |
| Express    | 3000 | Middleware & request routing |
| FastAPI    | 8000 | ML & storage backend         |
| Akave Link | 4000 | Filecoin storage integration |

## Development Notes

### Port Conflicts

```bash
# Check ports in use
lsof -i :8000
lsof -i :3000
lsof -i :4000

# Kill process on specific port
lsof -ti :8000 | xargs kill -9
```

### File Upload Constraints

- Minimum size: 127 bytes
- Maximum size: 100MB
- Supported types: Images, Video, Text

### Testing

```bash
# Frontend tests
cd frontend
npm test

# Python backend tests
cd backend/python
poetry run test

# Express tests
cd backend/express
npm test
```

## Additional Documentation

- [Frontend README](./frontend/README.md)
- [Express Server README](./backend/express/README.md)
- [Python Backend README](./backend/python/README.md)
- [API Documentation](./docs/api.md)

## Common Issues

### Multiple Python Servers

When using `poetry run dev`, two processes are normal:

- Watcher process for auto-reload
- Application server process

### Docker Container Management

```bash
# View container logs
docker logs akavelink

# Restart container
poetry run akave restart

# Stop container
poetry run akave stop
```

### CORS Issues

Default allowed origins:

- `http://localhost:5173` (Frontend)
- `http://localhost:3000` (Express)
- `http://localhost:8000` (FastAPI)

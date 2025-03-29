# ASL Teaching Website

SignLang: Empowering Accessibility through Open-Source and Decentralization

Every day, millions rely on sign language to communicate—but access to high-quality sign language translation remains limited, expensive, and monopolized by big tech. Current solutions are often inaccessible due to high costs, limited availability, and proprietary restrictions, creating significant barriers in critical areas such as healthcare, education, and everyday interactions.

SignLang is here to disrupt this. We're building an open-source, decentralized American Sign Language (ASL) translator, leveraging the power of the Filecoin ecosystem and its decentralized storage (Akave, Storacha, Lighthouse, Recall) and compute services (Lilypad).

The Problem We're Solving:

Educational Barriers: Many educational institutions lack affordable, reliable ASL translation resources, limiting opportunities for Deaf and hard-of-hearing students.

Healthcare Communication: Miscommunication in healthcare settings due to limited interpreter availability can lead to severe misunderstandings and reduced quality of care.

Accessibility in Daily Life: Dependence on costly human interpreters or centralized, proprietary translation solutions leaves many users isolated, unable to communicate spontaneously or in real-time.

Our Vision

We envision a future where sign language translation models aren't gatekept by conglomerates but grown organically by the community itself. The availability of comprehensive training data remains a significant barrier—but we've turned this challenge into our greatest opportunity.

How it Works:

Community-Driven Data Collection: Our initial app helps users learn and practice ASL. As users improve, they contribute high-quality, user-generated videos back into our dataset, enriching the model organically.

Decentralized Storage (Filecoin Network): We utilize decentralized storage providers like Akave, Storacha, Lighthouse, and Recall. Filecoin's incentivized storage network ensures secure, censorship-resistant, and privacy-focused data hosting.

Decentralized Compute with Lilypad: By leveraging Lilypad's decentralized compute network, SignLang runs translations without reliance on centralized cloud providers—lowering costs and preserving user privacy.

Achievement System: We've implemented an ERC4973 Soulbound Token system to reward users for their contributions and progress in learning ASL. These non-transferable achievement tokens are stored on IPFS and provide a permanent record of a user's journey in learning ASL.

Progress So Far:

Filecoin Storage: We've explored multiple storage providers:

Storacha: Successfully storing and retrieving data.

Akave: Exploring secure storage via private keys.

Lighthouse: Simple, reliable data handling.

Lilypad Compute: A working Lilypad module now executes our translation model using decentralized compute resources.

Achievement Token System: Implemented ERC4973 Soulbound Tokens with:
- Achievement tiers (Beginner, Intermediate, Advanced, Expert, Master)
- IPFS metadata storage for achievement details
- Gas-efficient implementation for Filecoin FVM
- Web3Modal integration for wallet connection
- Support for MetaMask, WalletConnect, and Coinbase Wallet

Long-Term Impact:

Our ambition goes beyond simply translating ASL. By creating a robust, decentralized dataset, we empower a global community to continuously improve and expand the translation model. Applications include real-time healthcare communication, educational resources, and accessible, barrier-free everyday interactions.

Why Decentralized & Open Source?

Decentralization ensures transparency, accessibility, and sustainability, turning users into active participants—not passive consumers. Open sourcing our model accelerates innovation, ensuring everyone benefits.

Join SignLang—let's democratize sign language translation, break barriers together, and build a more inclusive world.

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

2. Set up the frontend:

```bash
cd frontend
npm install
```

3. Set up the backend:

```bash
cd backend/python
poetry install
poetry shell
uvicorn main:app --reload
```

```bash
cd backend/express
npm install
npm run dev
```

4. Set up environment variables:

Create a `.env` file in the root directory with:
```env
PRIVATE_KEY=your_private_key_here
ETHERSCAN_API_KEY=your_etherscan_api_key
REACT_APP_WALLET_CONNECT_PROJECT_ID=your_wallet_connect_project_id
REACT_APP_CONTRACT_ADDRESS=your_deployed_contract_address
```

## Running the Application

1. Start the frontend development server:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

2. Start the backend server (in a new terminal):

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`

3. Start the Akave server (in a new terminal):

```bash
cd akave
npm install
npm run dev
```

The Akave server will be available at `http://localhost:3000`

4. Start the Express server (in a new terminal):

```bash
cd express
npm install
npm run dev
```

The Express server will be available at `http://localhost:4000`

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

## Smart Contract Deployment

1. Compile the contracts:
```bash
npm run compile
```

2. Deploy to Filecoin testnet:
```bash
npm run deploy:testnet
```

3. Deploy to Filecoin mainnet:
```bash
npm run deploy
```

## Development

### Frontend Development

- Run tests: `npm test`
- Build for production: `npm run build`
- Preview production build: `npm run preview`

### Backend Development

- API documentation available at `http://localhost:8000/docs`
- Run tests: `pytest`
- Format code: `black .`

### Smart Contract Development

- Compile contracts: `npm run compile`
- Run tests: `npm run test`
- Deploy to testnet: `npm run deploy:testnet`
- Deploy to mainnet: `npm run deploy`

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


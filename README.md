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
- **Decentralized Storage (Filecoin Network):** We utilize decentralized storage providers like Akave(implemented) (Future integrations - Storacha, Lighthouse, and Recall). Filecoin's incentivized storage network ensures secure, censorship-resistant, and privacy-focused data hosting.
- **Decentralized Compute with Lilypad:** By leveraging Lilypad's decentralized compute network, SignLang runs translations without reliance on centralized cloud providers—lowering costs and preserving user privacy.
- **Achievement & Reward System:** We've implemented an ERC721 Soulbound Token for achievements(smart contract made but not integrated into dApp) and ERC20 XP Token(integrated into dApp through contributions) to reward users for their contributions and progress in learning ASL. These tokens are stored on IPFS and provide both a permanent record of a user's journey in learning ASL(ERC721) and a potential route for users to be rewarded monetarily for their contributions(ERC20) as the model improves.

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

4.  **Blockchain functionality (`./blockchain`)**
    - Contains the Solidity smart contracts (ERC721 Achievement Token, XP Token).
    - Uses Hardhat for development, testing, and deployment.
    - **Setup Guide:** [`blockchain/README.md`](./blockchain/README.md)

### Directory Structure

```
.
├── README.md                 # Main project overview and setup links
├── backend/
│   ├── express/              # Express middleware
│   │   ├── README.md         # --> Setup Guide
│   │   ├── .env.example
│   │   └── ...
│   └── python/               # Python FastAPI core backend
│       ├── README.md         # --> Setup Guide
│       ├── .env.example
│       ├── pyproject.toml    # Poetry config
│       └── ...
├── blockchain/               # Smart contracts and deployment
│   ├── README.md             # --> Setup Guide
│   ├── .env.example
│   ├── hardhat.config.ts
│   └── ...
├── docs/                     # Supplementary documentation
│   ├── architecture.md
│   └── contribution.md
├── frontend/                 # React frontend application
│   ├── README.md             # --> Setup Guide
│   ├── .env.example
│   ├── vite.config.ts
│   └── ...
└── ... (other config files like .gitignore)
```

**Interaction Flow (Local Development):**

`User Browser (Frontend @ :5173)` -> `Express Middleware (@ :4000)` -> `Python Backend (@ :8000)`

The Python backend and potentially the frontend interact directly with the deployed blockchain contracts based on their respective `.env` configurations.

## Features(Future + Current)

- 🎥 Real-time ASL translation using camera
- 📚 Interactive ASL lessons with progress tracking
- 🌟 ERC721 Achievement Token and ERC20 Xp Token system for learning and contributing milestones
- 🤝 Community contribution platform
- 👤 Personal profile with learning statistics(TBD...)
- 💎 Soulbound achievements stored on IPFS
- 🔐 Secure wallet integration with Web3Modal & Wagmi

## Getting Started

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/ce20480/asl-teaching-website.git
    cd asl-teaching-website
    ```

2.  **Follow the setup guides:** Navigate into each relevant directory (`frontend`, `backend/express`, `backend/python`, `blockchain`) and follow the instructions in their respective `README.md` files to install dependencies, set up environment variables (`.env` from `.env.example`), and run each service.

For contribution guidelines, please see [`docs/contribution.md`](./docs/contribution.md).

## Backend Development Tests(In the works)

- API documentation available at `http://localhost:8000/docs`
- Run tests: `pytest`
- Format code: `black .`

## License

[MIT License]

## Acknowledgments

- Thanks to all contributors who have helped with the development
- Shadcn UI for the component library
- React and FastAPI communities for excellent documentation
- Filecoin Foundation for supporting decentralized storage
- OpenZeppelin for secure smart contract implementations

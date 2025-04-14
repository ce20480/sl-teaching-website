# Python FastAPI Backend Setup Guide

This guide explains how to set up and run the Python FastAPI backend locally. This server handles the core application logic, including machine learning model interactions and blockchain communications.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python (version >=3.9, <=3.12 as specified in `pyproject.toml`)
- Poetry (Python dependency management tool). If you don't have Poetry installed, follow the official installation instructions: [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

## Installation

1.  **Navigate to the Python backend directory:**
    From the project root, navigate to the Python backend directory:

    ```bash
    cd backend/python
    ```

2.  **Install dependencies:**
    Use Poetry to install the required Python packages defined in `pyproject.toml`:
    ```bash
    poetry install
    ```
    This command creates a virtual environment (if one doesn't exist) and installs all necessary libraries.

## Environment Variables

The Python backend relies on several environment variables for configuration, including API keys, contract addresses, and service URLs.

1.  **Create a `.env` file:**
    In the `backend/python` directory, copy the example environment file:

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the newly created `.env` file and replace the placeholder values with your actual configuration details. Refer to the comments in the `.env.example` file for explanations of each variable.

    **Crucial Variables:**

    - `WEB3_PRIVATE_KEY`: Your private key for interacting with the blockchain (e.g., sending transactions). **Keep this secure and never commit it.**
    - `WEB3_PROVIDER_URL`: RPC URL for the blockchain network.
    - `CHAIN_ID`: Chain ID for the blockchain network.
    - `TFIL_ACHIEVEMENT_CONTRACT_ADDRESS`: Address of the deployed Achievement contract.
    - `ERC20_XP_CONTRACT_ADDRESS`: Address of the deployed XP Token contract.
    - `MODEL_PATH`: Path to the ML model file.

    Configure optional variables as needed for your specific setup (e.g., distinct keys, Akave details).

## Running the Development Server

Once dependencies are installed and the `.env` file is configured, you can run the FastAPI development server using the Poetry script defined in `pyproject.toml`:

```bash
poetry run dev
```

Alternatively, you can activate the poetry shell first and then run the script:

```bash
poetry shell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

This command will:

- Start the Uvicorn server, which runs the FastAPI application (`src/main.py`).
- Typically listens on `http://localhost:8000` (check terminal output).
- The `--reload` flag enables auto-reloading when code changes are detected.

Ensure the Express middleware (if used) is configured with the correct `PYTHON_API_URL` (e.g., `http://localhost:8000/api`) in its `.env` file.

### Accessing API Documentation

While the server is running, you can access the automatically generated interactive API documentation (Swagger UI) by navigating to `http://localhost:8000/docs` in your browser. This provides a detailed view of all available API endpoints, their parameters, and allows you to test them directly.

## Running Tests

To execute the automated tests located in the `tests/` directory:

```bash
poetry run test
```

Or, if inside the poetry shell:

```bash
pytest
```

This command uses `pytest` to discover and run all tests.

## Development

- Server runs on port 8000
- Uses Poetry for dependency management
- FastAPI for API endpoints (interactive docs at `/docs`)

## Configuration

- Environment variables in `.env`
- CORS settings in `main.py`
- Poetry configuration in `pyproject.toml`

## Key Features

- File storage handling
- ML model integration
- Filecoin integration
- Type-safe API endpoints

## Common Issues

1. Multiple server instances
   - Use `poetry run dev` only
   - Check for zombie processes
2. Import errors
   - Ensure proper Python path
   - Use absolute imports
3. Poetry setup
   - Configure virtualenv correctly
   - Include src directory in packages

## Project Structure

```
backend/python/
├── pyproject.toml  # Poetry configuration
├── scripts/        # Development scripts
└── src/
    ├── api/       # API routes
    ├── core/      # Core configuration
    └── services/  # Business logic
```

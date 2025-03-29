# Project Setup Guide

This guide explains how to set up the ASL Teaching Website project for development.

## Prerequisites

Before you begin, ensure you have installed:

- Node.js (v18 or higher)
- Python (v3.11 or higher)
- Poetry (recommended) or pip
- Git

## Clone the Repository

```bash
git clone https://github.com/yourusername/asl-teaching-website.git
cd asl-teaching-website
```

## Frontend Setup

1. Install dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Create a `.env.local` file:

   ```
   VITE_API_URL=http://localhost:4000
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Express Middleware Setup

1. Install dependencies:

   ```bash
   cd backend/express
   npm install
   ```

2. Create a `.env` file:

   ```
   PORT=4000
   PYTHON_API_URL=http://localhost:8000
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Python Backend Setup

1. Install dependencies using Poetry (recommended):

   ```bash
   cd backend/python
   poetry install
   ```

   Or using pip:

   ```bash
   cd backend/python
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Install the sl-detection package:

   ```bash
   # Using Poetry
   poetry add sl-detection

   # Using pip
   pip install sl-detection
   ```

3. Create a `.env` file:

   ```
   MODEL_PATH=./models/asl_model.pt
   ```

4. Download the model file:

   ```bash
   mkdir -p models
   # Download model file from your storage location
   # For example:
   # curl -o models/asl_model.pt https://your-storage-url/asl_model.pt
   ```

5. Start the development server:

   ```bash
   # Using Poetry
   poetry run uvicorn src.main:app --reload

   # Using pip
   uvicorn src.main:app --reload
   ```

## Verify the Setup

1. Frontend should be running at: http://localhost:5173
2. Express middleware should be running at: http://localhost:4000
3. Python backend should be running at: http://localhost:8000

To verify API connectivity:

1. Start all three servers
2. Visit http://localhost:5173
3. Try the "Start Camera" button and check if hand detection works
4. Check the console for any errors

## Debugging Common Issues

### Model Not Found

If you get a "Model not found" error:

1. Make sure the model file exists at the path specified in the `.env` file
2. Check file permissions
3. Verify the file path is correct for your operating system

### API Connection Issues

If the frontend can't connect to the API:

1. Check that all servers are running
2. Verify the CORS configuration in the Express server
3. Ensure environment variables are set correctly

### Package Installation Issues

If you have issues installing packages:

1. Make sure you're using a compatible Python version (3.11+)
2. Try updating pip: `pip install --upgrade pip`
3. If using Poetry, try `poetry update`

# Express Middleware Setup Guide

This guide explains how to set up and run the Express middleware server locally. This server acts as a bridge between the frontend and the Python backend.

## Prerequisites

Before you begin, ensure you have the following installed:

- Node.js (LTS version recommended)
- npm (comes with Node.js)

## Installation

1.  **Navigate to the Express directory:**
    From the project root, navigate to the Express middleware directory:

    ```bash
    cd backend/express
    ```

2.  **Install dependencies:**
    Run the following command to install the necessary Node modules:
    ```bash
    npm install
    ```

## Environment Variables

The Express server requires environment variables to configure its port, the Python backend URL, and allowed origins for CORS.

1.  **Create a `.env` file:**
    In the `backend/express` directory, copy the example environment file:

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Open the newly created `.env` file and adjust the values if necessary for your local setup. The defaults are usually suitable for standard local development where the frontend runs on port 5173 and the Python backend runs on port 8000.

    - `PORT`: The port the Express server will listen on (should match frontend proxy target, usually 4000).
    - `PYTHON_API_URL`: The full URL where the Python backend is accessible.
    - `NODE_ENV`: Application environment (e.g., `development`).
    - `CORS_ORIGIN`: The frontend URL(s) allowed to make requests.

## Running the Development Server

Once you have installed the dependencies and configured your `.env` file, you can start the local development server:

```bash
npm run dev
```

This command will:

- Start the Express server using `ts-node-dev`, which automatically restarts the server on file changes.
- The server will listen on the port specified in your `.env` file (default is 4000).
- It will proxy requests from the frontend (running on `CORS_ORIGIN`) to the `PYTHON_API_URL`.

Make sure your Python backend server is running and accessible at the `PYTHON_API_URL` specified in the `.env` file.

## Building and Running for Production

1.  **Build the TypeScript code:**

    ```bash
    npm run build
    ```

    This compiles the TypeScript code into JavaScript in the `dist` directory.

2.  **Start the server:**
    ```bash
    npm start
    ```
    This runs the compiled JavaScript code using Node.js.

## Testing

To run the automated tests:

```bash
npm test
```

## Development

- Server runs on port 3000
- Proxies requests to Python backend (port 8000)
- Handles file upload processing

## Configuration

```typescript
export const config = {
  port: 3000,
  pythonApiUrl: "http://localhost:8000",
  corsOrigins: ["http://localhost:5173", "http://localhost:5174"],
};
```

## Key Features

- CORS handling
- File upload processing
- Request forwarding to Python
- Error handling

## Common Issues

1. Port conflicts
   - Ensure no other service runs on port 3000
2. File size limits
   - Configure multer limits
3. CORS configuration
   - Update allowed origins for development/production

## Project Structure

```
src/
├── routes/         # API routes
├── config.ts       # Configuration
└── server.ts       # Server setup
```

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import storage, prediction, rewards, evaluation, blockchain_routes

app = FastAPI(title="ASL Teaching API", description="API for ASL teaching application")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # Express server
        "http://localhost:8000",    # FastAPI direct access
        "http://127.0.0.1:8000",    
        "http://localhost:5173",    # Vite development server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers with API prefix
app.include_router(storage.router, prefix="/api")
app.include_router(prediction.router, prefix="/api")
app.include_router(rewards.router, prefix="/api")
app.include_router(evaluation.router, prefix="/api")
app.include_router(blockchain_routes.router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import importlib.util
import sys

# Create FastAPI app
app = FastAPI(
    title="Resume Builder API",
    description="API for managing resume experiences and job matching",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dynamically import routers once they're created
try:
    from api.routers import experiences, jobs, utils
    
    # Include routers
    app.include_router(experiences.router, prefix="/api/experiences", tags=["experiences"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(utils.router, prefix="/api/utils", tags=["utils"])
except ImportError:
    # This will happen when the routers haven't been created yet
    pass

@app.get("/")
async def root():
    return {"message": "Welcome to Resume Builder API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
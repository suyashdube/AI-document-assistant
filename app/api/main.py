from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import os
from dotenv import load_dotenv

from .routers import auth, documents, ai_operations
from ..ai_controls.permit_client import permit_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Document Assistant",
    description="An AI-powered document assistant with robust authorization controls using Permit.io",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo, in production limit this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(ai_operations.router)

# Add middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request details
    logger.info(
        f"Request {request.method} {request.url.path} completed in {process_time:.4f}s "
        f"with status code {response.status_code}"
    )
    
    return response

@app.get("/")
async def root():
    """
    Root endpoint providing basic API information.
    """
    return {
        "app": "AI Document Assistant",
        "version": "1.0.0",
        "description": "AI-powered document assistant with Permit.io authorization controls",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "permit_client": permit_client.permit is not None
    } 
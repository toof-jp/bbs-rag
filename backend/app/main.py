"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import chat
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    chat.router,
    prefix=f"{settings.api_v1_str}",
    tags=["chat"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "BBS RAG API",
        "version": settings.project_version,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

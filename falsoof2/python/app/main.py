"""
main.py – FastAPI application entry point for the National Healthcare ID System.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .database import engine, Base
from .routers import auth, admin, citizens, insurance, public

app = FastAPI(
    title="National Healthcare ID System",
    version="1.0.0",
    description=(
        "A national-level healthcare identity platform. Every citizen gets a "
        "unique Health-ID (like Aadhaar for health). Government-approved hospitals "
        "update vitals every 3–5 months; all hospitals can read records and log visits; "
        "insurance balances are tracked in real-time."
    ),
)

# ─── Static Files & Frontend ──────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ─── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    """Create all database tables on first run (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ─── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/auth",      tags=["Authentication"])
app.include_router(admin.router,     prefix="/api/admin",     tags=["Admin"])
app.include_router(citizens.router,  prefix="/api/citizens",  tags=["Citizens"])
app.include_router(insurance.router, prefix="/api/insurance", tags=["Insurance"])
app.include_router(public.router,    prefix="/api/public",    tags=["Public"])

# ─── Health check & Root ───────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root(request: Request):
    index_file = STATIC_DIR / "index.html"
    accept = request.headers.get("accept", "")
    # If client prefers HTML or browser request, serve the web app
    if index_file.exists() and "application/json" not in accept:
        return FileResponse(str(index_file))
    # Otherwise return API status
    return {
        "status": "online",
        "service": "National Healthcare ID System API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health",
        "website_url": "/",
    }

@app.get("/portal", tags=["Root"])
@app.get("/app", tags=["Root"])
async def portal():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(status_code=404, content={"detail": "Frontend file not found"})

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "National Healthcare ID System"}

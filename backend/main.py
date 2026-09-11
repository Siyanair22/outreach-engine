"""
GTM Outreach Engine — API Entry Point

A tool for automating prospect research and personalized outreach email
generation. Built with FastAPI, SQLAlchemy, and the Google Gemini API.

Run with: uvicorn main:app --reload
API docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import prospects, dashboard

app = FastAPI(
    title="GTM Outreach Engine",
    description="AI-powered prospect research and outreach email generation",
    version="0.1.0",
)

# Allow frontend (React dev server) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(prospects.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def on_startup():
    """Initialize database tables on app startup."""
    init_db()
    print("Database initialized.")
    print("API docs available at http://localhost:8000/docs")


@app.get("/")
def root():
    return {
        "name": "GTM Outreach Engine",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}

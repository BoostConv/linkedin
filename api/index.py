"""Vercel Python serverless entry point.

This catch-all route forwards all /api/* requests to the FastAPI application.
"""
import sys
import os

# Add backend directory to Python path so imports work
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app  # noqa: E402 — must be after path manipulation

# Vercel's Python runtime detects the ASGI app automatically

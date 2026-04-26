"""Vercel serverless entry point — re-exports the FastAPI ASGI app."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: F401, E402 — must come after sys.path patch

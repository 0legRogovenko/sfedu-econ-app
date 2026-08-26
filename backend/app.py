"""Vercel FastAPI entrypoint.

Vercel looks for a top-level ``app`` object in a recognized module.  Re-export
the production application instead of maintaining a second router tree.
"""

from src.main import app

__all__ = ["app"]

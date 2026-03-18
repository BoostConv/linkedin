"""Vercel Python serverless entry point.

This catch-all route forwards all /api/* requests to the FastAPI application.
Wraps the app with trailing slash normalization to avoid redirect loops.
"""
import sys
import os

# Add backend directory to Python path so imports work
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app as fastapi_app  # noqa: E402


class TrailingSlashWrapper:
    """ASGI wrapper that adds trailing slash to /api/* paths internally.

    FastAPI routes are declared with trailing slash (e.g. @router.get("/")).
    Vercel sends requests without trailing slash (e.g. /api/pillars).
    This wrapper normalizes the path so routes always match.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path.startswith("/api") and not path.endswith("/"):
                scope = dict(scope)
                scope["path"] = path + "/"
        await self.app(scope, receive, send)


# Export the wrapped app for Vercel
app = TrailingSlashWrapper(fastapi_app)

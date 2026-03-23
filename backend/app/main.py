import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import auth, posts, pillars, templates, writing_rules, ideas, analytics, calendar, generate, carousel, ml, competitors, comments, email_inbox, products, branding, cron

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

settings = get_settings()


class TrailingSlashMiddleware:
    """ASGI middleware that adds trailing slash to API paths for FastAPI routing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            if path.startswith("/api/") and not path.endswith("/") and "." not in path.split("/")[-1]:
                scope["path"] = path + "/"
        await self.app(scope, receive, send)


_app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs/",
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
)

_app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
_app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
_app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
_app.include_router(pillars.router, prefix="/api/pillars", tags=["Pillars"])
_app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
_app.include_router(writing_rules.router, prefix="/api/writing-rules", tags=["Writing Rules"])
_app.include_router(ideas.router, prefix="/api/ideas", tags=["Ideas"])
_app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
_app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
_app.include_router(generate.router, prefix="/api/ai", tags=["AI Generation"])
_app.include_router(carousel.router, prefix="/api/carousel", tags=["Carousel"])
_app.include_router(ml.router, prefix="/api/ml", tags=["ML"])
_app.include_router(competitors.router, prefix="/api/competitors", tags=["Competitors"])
_app.include_router(comments.router, prefix="/api/comments", tags=["Comments"])
_app.include_router(email_inbox.router, prefix="/api/email-inbox", tags=["Email Inbox"])
_app.include_router(products.router, prefix="/api/products", tags=["Products"])
_app.include_router(branding.router, prefix="/api/branding", tags=["Branding"])
_app.include_router(cron.router, prefix="/api/cron", tags=["Cron Jobs"])


@_app.get("/api/health/")
async def health():
    return {"status": "ok"}


@_app.get("/api/debug/db/")
async def debug_db():
    """Debug endpoint to check DB connectivity."""
    from app.database import async_session
    from sqlalchemy import text
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT count(*) FROM ideas"))
            count = result.scalar()
            return {"status": "ok", "ideas_count": count}
    except Exception as e:
        return {"status": "error", "detail": str(e), "type": type(e).__name__}


# Wrap with trailing slash middleware for Vercel compatibility
app = TrailingSlashMiddleware(_app)

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import auth, posts, pillars, templates, writing_rules, ideas, analytics, calendar, generate, carousel, ml, competitors, comments, email_inbox, products, branding, cron

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
app.include_router(pillars.router, prefix="/api/pillars", tags=["Pillars"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(writing_rules.router, prefix="/api/writing-rules", tags=["Writing Rules"])
app.include_router(ideas.router, prefix="/api/ideas", tags=["Ideas"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(generate.router, prefix="/api/ai", tags=["AI Generation"])
app.include_router(carousel.router, prefix="/api/carousel", tags=["Carousel"])
app.include_router(ml.router, prefix="/api/ml", tags=["ML"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["Competitors"])
app.include_router(comments.router, prefix="/api/comments", tags=["Comments"])
app.include_router(email_inbox.router, prefix="/api/email-inbox", tags=["Email Inbox"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(branding.router, prefix="/api/branding", tags=["Branding"])
app.include_router(cron.router, prefix="/api/cron", tags=["Cron Jobs"])


@app.get("/api/health")
@app.get("/api/health/")
async def health():
    return {"status": "ok"}


@app.get("/api/debug-db")
@app.get("/api/debug-db/")
async def debug_db():
    """Temporary debug endpoint to check DB connection."""
    import traceback
    try:
        from app.database import async_session
        async with async_session() as db:
            from sqlalchemy import text
            result = await db.execute(text("SELECT COUNT(*) FROM pillars"))
            count = result.scalar()
            return {"status": "connected", "pillars_count": count, "db_url_prefix": settings.database_url[:30]}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc(), "db_url_prefix": settings.database_url[:30]}

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import auth, posts, pillars, templates, writing_rules, ideas, analytics, calendar, generate, carousel, ml, competitors, comments, email_inbox, products, branding
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}

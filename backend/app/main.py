from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.rate_limit import limiter
from app.routers import auth, chat, pages

settings = get_settings()

app = FastAPI(
    title="AI-Sommelier API",
    description="API для AI-сомелье — персональные рекомендации вин",
    version="0.1.0",
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Превышен лимит запросов",
            "retry_after": 900,  # 15 minutes
        },
    )


# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(pages.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

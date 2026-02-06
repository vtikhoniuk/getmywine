"""Pages router for serving HTML templates."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request},
    )


@router.get("/password-reset", response_class=HTMLResponse)
async def password_reset_page(request: Request):
    """Password reset page."""
    return templates.TemplateResponse(
        "auth/reset-password.html",
        {"request": request},
    )


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat page with GetMyWine sommelier."""
    return templates.TemplateResponse(
        "chat.html",
        {"request": request},
    )

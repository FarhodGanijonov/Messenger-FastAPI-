from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
import os

from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.chat import Chat, ChatMember
from app.models.message import Message
from app.models.call import Call
from app.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

serializer = URLSafeTimedSerializer(settings.ADMIN_SECRET_KEY)
SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 3600 * 8  # 8 hours


def create_session_token(username: str) -> str:
    return serializer.dumps(username, salt="admin-session")


def verify_session_token(token: str) -> str | None:
    try:
        return serializer.loads(token, salt="admin-session", max_age=SESSION_MAX_AGE)
    except Exception:
        return None


async def require_admin_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    username = verify_session_token(token)
    if not username or username != settings.ADMIN_USERNAME:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return username


def admin_redirect():
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=401,
        )
    token = create_session_token(username)
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, httponly=True)
    return response


@router.get("/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin=Depends(require_admin_session)):
    async with AsyncSessionLocal() as db:
        users_count = (await db.execute(select(func.count(User.id)))).scalar()
        active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar()
        chats_count = (await db.execute(select(func.count(Chat.id)))).scalar()
        messages_count = (await db.execute(select(func.count(Message.id)))).scalar()
        calls_count = (await db.execute(select(func.count(Call.id)))).scalar()

        # Recent users
        recent_users_result = await db.execute(
            select(User).order_by(desc(User.created_at)).limit(5)
        )
        recent_users = recent_users_result.scalars().all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "users_count": users_count,
            "active_users": active_users,
            "chats_count": chats_count,
            "messages_count": messages_count,
            "calls_count": calls_count,
        },
        "recent_users": recent_users,
        "admin_username": admin,
    })


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    page: int = 1,
    search: str = "",
    admin=Depends(require_admin_session),
):
    page_size = 20
    offset = (page - 1) * page_size

    async with AsyncSessionLocal() as db:
        query = select(User).order_by(desc(User.created_at))
        count_query = select(func.count(User.id))

        if search:
            query = query.where(
                (User.phone.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
            )
            count_query = count_query.where(
                (User.phone.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
            )

        total = (await db.execute(count_query)).scalar()
        users_result = await db.execute(query.limit(page_size).offset(offset))
        users = users_result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "search": search,
        "admin_username": admin,
    })


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    request: Request,
    admin=Depends(require_admin_session),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = not user.is_active
        await db.commit()

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)


@router.get("/chats", response_class=HTMLResponse)
async def admin_chats(
    request: Request,
    page: int = 1,
    admin=Depends(require_admin_session),
):
    page_size = 20
    offset = (page - 1) * page_size

    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count(Chat.id)))).scalar()
        chats_result = await db.execute(
            select(Chat).order_by(desc(Chat.created_at)).limit(page_size).offset(offset)
        )
        chats = chats_result.scalars().all()

        # Get member counts and message counts for each chat
        chat_stats = []
        for chat in chats:
            member_count = (await db.execute(
                select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat.id)
            )).scalar()
            message_count = (await db.execute(
                select(func.count(Message.id)).where(Message.chat_id == chat.id)
            )).scalar()
            chat_stats.append({
                "chat": chat,
                "member_count": member_count,
                "message_count": message_count,
            })

    total_pages = (total + page_size - 1) // page_size

    return templates.TemplateResponse("chats.html", {
        "request": request,
        "chat_stats": chat_stats,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "admin_username": admin,
    })

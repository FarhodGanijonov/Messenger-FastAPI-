from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import create_tables

from app.routers import auth, profile, contacts, chats, messages, media, calls, settings as settings_router, websocket
from app.admin.router import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Messenger Backend...")
    await create_tables()
    logger.info("Database tables created/verified.")
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory ready: {settings.UPLOAD_DIR}")
    yield
    logger.info("Shutting down Messenger Backend...")


app = FastAPI(
    title="Messenger API",
    description="Production-ready messenger backend with WebSocket support",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# API Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(contacts.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(media.router)
app.include_router(calls.router)
app.include_router(settings_router.router)
app.include_router(websocket.router)

# Admin Panel
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "debug": settings.DEBUG,
    }


@app.get("/")
async def root():
    return {
        "message": "Welcome to Messenger API",
        "docs": "/docs",
        "admin": "/admin/login",
    }

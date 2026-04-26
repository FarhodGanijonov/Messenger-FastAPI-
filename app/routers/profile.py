from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserPublicResponse, ProfileSetup, UserUpdate
from app.services.media_service import MediaService

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.post("/setup", response_model=UserResponse)
async def setup_profile(
    data: ProfileSetup,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.full_name = data.full_name
    if data.bio is not None:
        current_user.bio = data.bio
    await db.flush()
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.bio is not None:
        current_user.bio = data.bio
    await db.flush()
    return current_user


@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed for avatar")

    media_service = MediaService(db)
    media = await media_service.upload_file(file, current_user.id)
    current_user.avatar_url = media.url
    await db.flush()
    return current_user


@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

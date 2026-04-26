import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.media_service import MediaService
from app.config import settings
from fastapi import Request

router = APIRouter(prefix="/api/media", tags=["Media"])


@router.post("/upload", response_model=dict)
async def upload_media(
        request: Request,
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    service = MediaService(db)
    media = await service.upload_file(file, current_user.id)

    # Avtomatik base URL
    base_url = str(request.base_url).rstrip("/")

    return {
        "id": media.id,
        "file_name": media.file_name,
        "file_type": media.file_type,
        "file_size": media.file_size,
        "url": media.url,
    }


@router.get("/{filename}")
async def get_media(
    filename: str,
):
    from app.config import settings
    import os
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
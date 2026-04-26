import os
import uuid
import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.message import MediaFile
from app.config import settings
import logging

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    "video": ["video/mp4", "video/mpeg", "video/quicktime"],
    "audio": ["audio/mpeg", "audio/ogg", "audio/wav", "audio/webm"],
    "file": ["application/pdf", "application/zip", "text/plain",
             "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
}

ALL_ALLOWED = [t for types in ALLOWED_TYPES.values() for t in types]


class MediaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_media_type(self, content_type: str) -> str:
        for media_type, types in ALLOWED_TYPES.items():
            if content_type in types:
                return media_type
        return "file"

    async def upload_file(self, file: UploadFile, uploader_id: str) -> MediaFile:
        if file.content_type not in ALL_ALLOWED:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"File type '{file.content_type}' is not allowed")

        # Check file size
        content = await file.read()
        file_size = len(content)
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

        if settings.MEDIA_STORAGE == "s3":
            return await self._upload_to_s3(file, content, uploader_id, file_size)
        else:
            return await self._upload_to_local(file, content, uploader_id, file_size)

    async def _upload_to_local(self, file: UploadFile, content: bytes, uploader_id: str, file_size: int) -> MediaFile:
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = os.path.splitext(file.filename or "file")[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        media = MediaFile(
            uploader_id=uploader_id,
            file_name=file.filename or unique_filename,
            file_type=file.content_type,
            file_size=file_size,
            storage_type="local",
            file_path=file_path,
            url=f"{settings.BASE_URL}/api/media/{unique_filename}",
        )
        self.db.add(media)
        await self.db.flush()
        return media

    async def _upload_to_s3(self, file: UploadFile, content: bytes, uploader_id: str, file_size: int) -> MediaFile:
        import boto3
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        file_ext = os.path.splitext(file.filename or "file")[1]
        unique_key = f"media/{uuid.uuid4()}{file_ext}"

        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=unique_key,
            Body=content,
            ContentType=file.content_type,
        )

        url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_key}"

        media = MediaFile(
            uploader_id=uploader_id,
            file_name=file.filename or unique_key,
            file_type=file.content_type,
            file_size=file_size,
            storage_type="s3",
            file_path=unique_key,
            url=url,
        )
        self.db.add(media)
        await self.db.flush()
        return media

    async def get_media(self, media_id: str) -> MediaFile:
        result = await self.db.execute(select(MediaFile).where(MediaFile.id == media_id))
        return result.scalar_one_or_none()

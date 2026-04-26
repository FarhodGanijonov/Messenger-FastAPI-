from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, NotificationSettings, PrivacySettings, Device
from app.schemas.user import NotificationSettingsSchema, PrivacySettingsSchema, DeviceRegisterRequest
import uuid

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("/notifications", response_model=NotificationSettingsSchema)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = NotificationSettings(user_id=current_user.id)
        db.add(settings)
        await db.flush()
    return settings


@router.put("/notifications", response_model=NotificationSettingsSchema)
async def update_notification_settings(
    data: NotificationSettingsSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = NotificationSettings(user_id=current_user.id)
        db.add(settings)

    settings.message_notifications = data.message_notifications
    settings.call_notifications = data.call_notifications
    settings.group_notifications = data.group_notifications
    settings.sound_enabled = data.sound_enabled
    settings.vibration_enabled = data.vibration_enabled
    await db.flush()
    return settings


@router.get("/privacy", response_model=PrivacySettingsSchema)
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PrivacySettings).where(PrivacySettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = PrivacySettings(user_id=current_user.id)
        db.add(settings)
        await db.flush()
    return settings


@router.put("/privacy", response_model=PrivacySettingsSchema)
async def update_privacy_settings(
    data: PrivacySettingsSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    valid_values = ["everyone", "contacts", "nobody"]

    if data.last_seen_visible not in valid_values:
        raise HTTPException(status_code=400, detail="Invalid last_seen_visible value")
    if data.avatar_visible not in valid_values:
        raise HTTPException(status_code=400, detail="Invalid avatar_visible value")
    if data.bio_visible not in valid_values:
        raise HTTPException(status_code=400, detail="Invalid bio_visible value")

    result = await db.execute(
        select(PrivacySettings).where(PrivacySettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = PrivacySettings(user_id=current_user.id)
        db.add(settings)

    settings.last_seen_visible = data.last_seen_visible
    settings.avatar_visible = data.avatar_visible
    settings.bio_visible = data.bio_visible
    settings.read_receipts = data.read_receipts
    await db.flush()
    return settings


@router.post("/devices/register", response_model=dict)
async def register_device(
    data: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.platform not in ["ios", "android", "web"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Must be ios, android, or web")

    # Check if token already registered
    result = await db.execute(
        select(Device).where(Device.fcm_token == data.fcm_token)
    )
    device = result.scalar_one_or_none()

    if device:
        device.user_id = current_user.id
        device.platform = data.platform
    else:
        device = Device(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            fcm_token=data.fcm_token,
            platform=data.platform,
        )
        db.add(device)

    await db.flush()
    return {"message": "Device registered successfully", "device_id": device.id}

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.chat import Contact
from app.schemas.user import ContactSyncRequest, ContactResponse
import uuid

router = APIRouter(prefix="/api/contacts", tags=["Contacts"])


@router.get("", response_model=List[dict])
async def get_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact, User)
        .join(User, User.id == Contact.contact_id)
        .where(Contact.owner_id == current_user.id, User.is_active == True)
    )
    contacts = result.fetchall()

    return [
        {
            "id": contact.id,
            "contact_id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "display_name": contact.display_name,
        }
        for contact, user in contacts
    ]


@router.post("/sync", response_model=List[dict])
async def sync_contacts(
    data: ContactSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Find registered users matching the provided phones
    result = await db.execute(
        select(User).where(
            User.phone.in_(data.phones),
            User.id != current_user.id,
            User.is_active == True,
        )
    )
    users = result.scalars().all()

    synced = []
    for user in users:
        # Check if contact already exists
        existing = await db.execute(
            select(Contact).where(
                Contact.owner_id == current_user.id,
                Contact.contact_id == user.id,
            )
        )
        if not existing.scalar_one_or_none():
            contact = Contact(
                id=str(uuid.uuid4()),
                owner_id=current_user.id,
                contact_id=user.id,
            )
            db.add(contact)
            synced.append({"id": str(uuid.uuid4()), "contact_id": user.id, "phone": user.phone, "full_name": user.full_name, "avatar_url": user.avatar_url})
        else:
            synced.append({"contact_id": user.id, "phone": user.phone, "full_name": user.full_name, "avatar_url": user.avatar_url})

    await db.flush()
    return synced


@router.get("/search", response_model=List[dict])
async def search_contacts(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id != current_user.id,
            User.is_active == True,
            or_(
                User.phone.ilike(f"%{q}%"),
                User.full_name.ilike(f"%{q}%"),
            ),
        ).limit(20)
    )
    users = result.scalars().all()

    return [
        {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
        }
        for user in users
    ]

import re
from datetime import datetime, timezone
from typing import Optional


def normalize_phone(phone: str) -> str:
    """Remove all non-digit characters except leading +"""
    phone = re.sub(r"\s+", "", phone)
    if not phone.startswith("+"):
        phone = "+" + re.sub(r"\D", "", phone)
    else:
        phone = "+" + re.sub(r"\D", "", phone[1:])
    return phone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def truncate_text(text: Optional[str], max_length: int = 100) -> Optional[str]:
    if not text:
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

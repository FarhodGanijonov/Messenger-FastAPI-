from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MessengerAPI"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://messenger_user:messenger_pass@localhost:5432/messenger_db"
    SYNC_DATABASE_URL: str = "postgresql://messenger_user:messenger_pass@localhost:5432/messenger_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # OTP
    OTP_EXPIRE_MINUTES: int = 5
    OTP_DEV_MODE: bool = True

    # Media
    MEDIA_STORAGE: str = "local"
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50

    # S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "messenger-media"

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_SECRET_KEY: str = "admin-secret-key-change-in-production"
    BASE_URL: str = "http://localhost:8000"
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()



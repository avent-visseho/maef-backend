# ===================================
# app/core/config.py
# ===================================
from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Projet
    PROJECT_NAME: str = "MAEF E-commerce"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Base de données PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "maef"
    POSTGRES_PASSWORD: str = "maef"
    POSTGRES_DB: str = "maef"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return (
            f"postgresql+psycopg://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}:"
            f"{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )
    
    # JWT Configuration
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[Union[AnyHttpUrl, str]] = [
        "http://localhost:3000",  # React dev
        "http://localhost:3001", 
        "http://localhost:8080",  # Vue dev
        "http://127.0.0.1:3000",
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Sécurité
    BCRYPT_ROUNDS: int = 12
    
    # Instagram Integration (optionnel)
    IG_APP_ID: str = ""
    IG_APP_SECRET: str = ""
    IG_REDIRECT_URI: str = ""
    
    # Stripe (ou autres providers de paiement)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Email (optionnel)
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = ""
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Media settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/webm", "video/quicktime"]
    
    # APScheduler
    SCHEDULER_ENABLED: bool = True
    
    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
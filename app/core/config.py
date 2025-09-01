# ===================================
# app/core/config.py
# ===================================
"""
Configuration centralisée de l'application avec Pydantic Settings.
Gère toutes les variables d'environnement et leur validation.
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration principale de l'application."""
    
    # Application
    app_name: str = Field(default="Maef By Yas API", description="Nom de l'application")
    app_version: str = Field(default="1.0.0", description="Version de l'application")
    debug: bool = Field(default=False, description="Mode debug")
    environment: str = Field(default="development", description="Environnement (dev/staging/prod)")
    
    # API
    api_prefix: str = Field(default="/api/v1", description="Préfixe de l'API")
    allowed_hosts: list[str] = Field(default=["*"], description="Hosts autorisés")
    
    # Base de données
    database_url: PostgresDsn = Field(
        description="URL de connexion PostgreSQL",
        example="postgresql+psycopg://user:pass@localhost:5432/maef"
    )
    
    
    # JWT/Security
    jwt_secret_key: str = Field(
        description="Clé secrète pour JWT (doit être complexe en production)"
    )
    jwt_algorithm: str = Field(default="HS256", description="Algorithme JWT")
    jwt_access_token_expire_minutes: int = Field(
        default=60, description="Durée de vie access token (minutes)"
    )
    jwt_refresh_token_expire_minutes: int = Field(
        default=43200, description="Durée de vie refresh token (minutes) - 30 jours"
    )
    password_hash_rounds: int = Field(default=12, description="Rounds bcrypt")
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Origins autorisés pour CORS"
    )
    cors_allow_credentials: bool = Field(default=True, description="Autoriser credentials CORS")
    cors_allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Méthodes HTTP autorisées"
    )
    cors_allow_headers: list[str] = Field(
        default=["*"], description="Headers autorisés"
    )
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Activer le rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Requêtes par minute")
    
    # Upload & Media
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Taille max fichier (10MB)")
    allowed_image_types: list[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="Types d'images autorisés"
    )
    
    # Intégrations externes
    # Instagram
    instagram_app_id: Optional[str] = Field(default=None, description="App ID Instagram")
    instagram_app_secret: Optional[str] = Field(default=None, description="App Secret Instagram")
    instagram_redirect_uri: Optional[str] = Field(default=None, description="Redirect URI Instagram")
    
    # Stripe
    stripe_public_key: Optional[str] = Field(default=None, description="Clé publique Stripe")
    stripe_secret_key: Optional[str] = Field(default=None, description="Clé secrète Stripe")
    stripe_webhook_secret: Optional[str] = Field(default=None, description="Secret webhook Stripe")
    
    # FedaPay (alternative locale)
    fedapay_public_key: Optional[str] = Field(default=None, description="Clé publique FedaPay")
    fedapay_secret_key: Optional[str] = Field(default=None, description="Clé secrète FedaPay")
    fedapay_webhook_secret: Optional[str] = Field(default=None, description="Secret webhook FedaPay")
    
    # Email
    smtp_server: Optional[str] = Field(default=None, description="Serveur SMTP")
    smtp_port: int = Field(default=587, description="Port SMTP")
    smtp_username: Optional[str] = Field(default=None, description="Username SMTP")
    smtp_password: Optional[str] = Field(default=None, description="Password SMTP")
    smtp_use_tls: bool = Field(default=True, description="Utiliser TLS")
    from_email: str = Field(default="noreply@maefbyyas.com", description="Email expéditeur")
    
    # Search
    search_engine: str = Field(
        default="postgresql",
        description="Moteur de recherche (postgresql/meilisearch/elasticsearch)"
    )
    meilisearch_url: Optional[str] = Field(default=None, description="URL Meilisearch")
    meilisearch_api_key: Optional[str] = Field(default=None, description="Clé API Meilisearch")
    
    # Logging
    log_level: str = Field(default="INFO", description="Niveau de log")
    log_format: str = Field(default="json", description="Format de log (json/text)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("environment")
    def validate_environment(cls, v):
        """Valide que l'environnement est correct."""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Valide le niveau de log."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Retourne True si on est en production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Retourne True si on est en développement."""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Retourne l'instance des settings avec cache.
    Le cache évite de recharger les variables d'environnement à chaque appel.
    """
    return Settings()


# Raccourci pour accéder aux settings
settings = get_settings()
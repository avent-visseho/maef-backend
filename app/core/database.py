# ===================================
# app/core/database.py
# ===================================
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.core.config import settings

# Configuration du moteur SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # Log des requêtes SQL en mode debug
    future=True,  # SQLAlchemy 2.0 style
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    future=True
)

Base = declarative_base()


def get_db() -> Generator:
    """
    Générateur de session de base de données pour l'injection de dépendance FastAPI
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialise la base de données avec les extensions PostgreSQL nécessaires
    """
    with engine.begin() as conn:
        # Création des extensions PostgreSQL pour FTS et trigrams
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            print("✓ Extensions PostgreSQL créées (pg_trgm, unaccent)")
        except Exception as e:
            print(f"⚠️  Extensions PostgreSQL : {e}")
    
    # Création des tables
    Base.metadata.create_all(bind=engine)
    print("✓ Tables créées")


def check_db_connection() -> bool:
    """
    Vérifie la connexion à la base de données
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion DB: {e}")
        return False

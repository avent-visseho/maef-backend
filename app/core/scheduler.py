# ===================================
# Fichier: app/core/scheduler.py
# ===================================
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = None

def init_scheduler():
    """Initialiser APScheduler"""
    global scheduler
    
    if not settings.SCHEDULER_ENABLED:
        return
    
    jobstores = {
        'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
    }
    
    executors = {
        'default': ThreadPoolExecutor(20),
    }
    
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    # Ajouter les jobs périodiques
    add_periodic_jobs()
    
    scheduler.start()
    logger.info("✓ APScheduler démarré")

def add_periodic_jobs():
    """Ajouter les tâches périodiques"""
    # Nettoyage des tokens expirés (tous les jours à 2h)
    scheduler.add_job(
        func=cleanup_expired_tokens_job,
        trigger='cron',
        hour=2,
        minute=0,
        id='cleanup_expired_tokens'
    )
    
    # Nettoyage des paniers abandonnés (tous les jours à 3h)
    scheduler.add_job(
        func=cleanup_abandoned_carts_job,
        trigger='cron',
        hour=3,
        minute=0,
        id='cleanup_abandoned_carts'
    )
    
    # Ingestion des stories Instagram (toutes les 10 minutes)
    if settings.IG_APP_ID and settings.IG_APP_SECRET:
        scheduler.add_job(
            func=ingest_instagram_stories_job,
            trigger='interval',
            minutes=10,
            id='ingest_instagram_stories'
        )

def cleanup_expired_tokens_job():
    """Job de nettoyage des tokens expirés"""
    try:
        from app.core.database import SessionLocal
        from app.repositories.user_repo import cleanup_expired_tokens
        
        with SessionLocal() as db:
            count = cleanup_expired_tokens(db)
            logger.info(f"Nettoyage tokens: {count} tokens expirés supprimés")
    except Exception as e:
        logger.error(f"Erreur nettoyage tokens: {e}")

def cleanup_abandoned_carts_job():
    """Job de nettoyage des paniers abandonnés"""
    try:
        from app.core.database import SessionLocal
        from app.repositories.cart_repo import CartRepository
        
        with SessionLocal() as db:
            cart_repo = CartRepository(db)
            count = cart_repo.cleanup_empty_carts(days_ago=7)
            logger.info(f"Nettoyage paniers: {count} paniers vides supprimés")
    except Exception as e:
        logger.error(f"Erreur nettoyage paniers: {e}")

def ingest_instagram_stories_job():
    """Job d'ingestion des stories Instagram"""
    try:
        # TODO: Implémenter l'ingestion Instagram
        logger.info("Ingestion Instagram stories - À implémenter")
    except Exception as e:
        logger.error(f"Erreur ingestion Instagram: {e}")

def shutdown_scheduler():
    """Arrêter le scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("✓ APScheduler arrêté")
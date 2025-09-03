# ===================================
# app/main.py
# ===================================
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db, check_db_connection
from app.core.scheduler import init_scheduler

# Import des routes
from app.api.v1 import auth, users, products, categories, media, stories
from app.api.v1 import search, cart, checkout, orders, payments, promotions
from app.api.v1 import reviews, inventory, webhooks

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Démarrage
    logger.info("🚀 Démarrage de l'application MAEF...")
    
    # Vérifier la connexion DB
    if not check_db_connection():
        logger.error("❌ Impossible de se connecter à la base de données")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    # Initialiser la base de données
    init_db()
    
    # Démarrer le scheduler si activé
    if settings.SCHEDULER_ENABLED:
        init_scheduler()
        logger.info("✓ Scheduler APScheduler démarré")
    
    logger.info("✅ Application démarrée avec succès")
    
    yield
    
    # Arrêt
    logger.info("⏹️ Arrêt de l'application...")


def create_app() -> FastAPI:
    """Factory pour créer l'application FastAPI"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,  # Changé de VERSION à PROJECT_VERSION
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes API v1
    app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
    app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
    app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["Products"])
    app.include_router(categories.router, prefix=f"{settings.API_V1_STR}/categories", tags=["Categories"])
    app.include_router(media.router, prefix=f"{settings.API_V1_STR}/media", tags=["Media"])
    app.include_router(stories.router, prefix=f"{settings.API_V1_STR}/stories", tags=["Stories"])
    app.include_router(search.router, prefix=f"{settings.API_V1_STR}/search", tags=["Search"])
    app.include_router(cart.router, prefix=f"{settings.API_V1_STR}/cart", tags=["Cart"])
    app.include_router(checkout.router, prefix=f"{settings.API_V1_STR}/checkout", tags=["Checkout"])
    app.include_router(orders.router, prefix=f"{settings.API_V1_STR}/orders", tags=["Orders"])
    app.include_router(payments.router, prefix=f"{settings.API_V1_STR}/payments", tags=["Payments"])
    app.include_router(promotions.router, prefix=f"{settings.API_V1_STR}/promotions", tags=["Promotions"])
    app.include_router(reviews.router, prefix=f"{settings.API_V1_STR}/reviews", tags=["Reviews"])
    app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/inventory", tags=["Inventory"])
    app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])
    
    # Route de santé
    @app.get("/health")
    async def health_check():
        """Vérification de la santé de l'API"""
        db_status = "ok" if check_db_connection() else "error"
        
        return {
            "status": "ok" if db_status == "ok" else "error",
            "version": settings.PROJECT_VERSION,  # Changé de VERSION à PROJECT_VERSION
            "environment": settings.ENVIRONMENT,
            "database": db_status,
            "scheduler": "ok" if settings.SCHEDULER_ENABLED else "disabled"
        }
    
    # Route racine
    @app.get("/")
    async def root():
        return {
            "message": f"Bienvenue sur {settings.PROJECT_NAME}",
            "version": settings.PROJECT_VERSION,  # Changé de VERSION à PROJECT_VERSION
            "docs": "/docs",
            "health": "/health"
        }
    
    # Gestion globale des erreurs
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "http_error"
                }
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Erreur non gérée: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Erreur interne du serveur",
                    "type": "internal_error"
                }
            },
        )
    
    return app


# Créer l'instance de l'application
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
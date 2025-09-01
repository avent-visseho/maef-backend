# ===================================
# app/api/deps.py
# ===================================
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.models.user import User
from app.models.cart import Cart
from app.repositories.user_repo import get_user_by_id

security = HTTPBearer()


def get_current_user_or_none(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Récupérer l'utilisateur connecté ou None si pas authentifié
    Utile pour les endpoints qui acceptent les utilisateurs anonymes
    """
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def get_user_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Cart:
    """
    Récupérer ou créer le panier de l'utilisateur connecté
    """
    from app.repositories.cart_repo import get_or_create_user_cart
    return get_or_create_user_cart(db, current_user.id)


def get_cart_by_session(
    session_id: str,
    db: Session = Depends(get_db)
) -> Optional[Cart]:
    """
    Récupérer un panier par session ID (pour les utilisateurs non connectés)
    """
    from app.repositories.cart_repo import get_cart_by_session_id
    return get_cart_by_session_id(db, session_id)


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Vérifier que l'utilisateur est admin
    """
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis"
        )
    return current_user


def require_manager_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Vérifier que l'utilisateur est manager ou admin
    """
    if not (current_user.has_role("admin") or current_user.has_role("manager")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès manager ou administrateur requis"
        )
    return current_user


def get_pagination_params(
    skip: int = 0,
    limit: int = 20
) -> tuple[int, int]:
    """
    Paramètres de pagination communs
    """
    if skip < 0:
        skip = 0
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    
    return skip, limit
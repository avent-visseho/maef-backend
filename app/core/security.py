# ===================================
# app/core/security.py
# ===================================

from datetime import datetime, timedelta
from typing import Any, Union, Optional, List
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# Configuration du hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration du bearer token
security = HTTPBearer()

# Scopes/permissions pour l'autorisation
SCOPES = {
    "users:read": "Lire les utilisateurs",
    "users:write": "Écrire les utilisateurs", 
    "products:read": "Lire les produits",
    "products:write": "Écrire les produits",
    "orders:read": "Lire les commandes",
    "orders:write": "Écrire les commandes",
    "admin": "Accès administrateur complet",
    "media:read": "Lire les médias",
    "media:write": "Écrire les médias",
    "stories:read": "Lire les stories",
    "stories:write": "Écrire les stories",
}


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: timedelta = None,
    scopes: List[str] = None
) -> str:
    """Créer un token d'accès JWT"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire, 
        "sub": str(subject),
        "scopes": scopes or []
    }
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Créer un token de rafraîchissement"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hacher un mot de passe"""
    return pwd_context.hash(password, rounds=settings.BCRYPT_ROUNDS)


def decode_token(token: str) -> dict:
    """Décoder et valider un token JWT"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
):
    """Obtenir l'utilisateur actuel à partir du token"""
    from app.repositories.user_repo import get_user_by_id  # Import local pour éviter les imports circulaires
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
    except JWTError:
        raise credentials_exception
        
    user = get_user_by_id(db, user_id=int(user_id))
    if user is None:
        raise credentials_exception
        
    # Ajouter les scopes au user pour vérifications ultérieures
    user.token_scopes = token_scopes
    return user


def get_current_active_user(current_user = Depends(get_current_user)):
    """Obtenir l'utilisateur actuel actif"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Utilisateur inactif"
        )
    return current_user


def require_scope(required_scope: str):
    """Décorateur pour vérifier les permissions/scopes"""
    def scope_checker(current_user = Depends(get_current_active_user)):
        if not hasattr(current_user, 'token_scopes'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas de scopes dans le token"
            )
            
        user_scopes = getattr(current_user, 'token_scopes', [])
        
        # L'admin a accès à tout
        if "admin" in user_scopes:
            return current_user
            
        if required_scope not in user_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission manquante: {required_scope}"
            )
        return current_user
    
    return scope_checker


def require_roles(*required_roles: str):
    """Décorateur pour vérifier les rôles utilisateur"""
    def role_checker(current_user = Depends(get_current_active_user)):
        user_roles = [role.name for role in current_user.roles] if hasattr(current_user, 'roles') else []
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle requis: {' ou '.join(required_roles)}"
            )
        return current_user
    
    return role_checker
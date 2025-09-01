# ===================================
# app/api/v1/auth.py
# ===================================
from typing import Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    decode_token,
    get_current_user,
    get_current_active_user
)
from app.repositories.user_repo import (
    get_user_by_email,
    create_user,
    update_last_login,
    save_refresh_token,
    get_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens
)
from app.schemas.user import (
    UserCreate, 
    LoginRequest, 
    RefreshTokenRequest,
    AuthResponse,
    Token,
    User,
    UserChangePassword
)

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Inscription d'un nouvel utilisateur
    """
    # Vérifier si l'email existe déjà
    if get_user_by_email(db, email=user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Créer l'utilisateur
    user = create_user(db=db, user=user_data)
    
    # Créer les tokens
    user_scopes = ["users:read", "products:read", "cart:write", "orders:read"]
    if user.has_role("admin"):
        user_scopes.append("admin")
    
    access_token = create_access_token(
        subject=user.id,
        scopes=user_scopes
    )
    
    refresh_token = create_refresh_token(subject=user.id)
    
    # Sauvegarder le refresh token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, user.id, refresh_token, expires_at)
    
    token_data = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=User.from_orm(user)
    )
    
    return AuthResponse(
        message="Inscription réussie",
        data=token_data
    )


@router.post("/login", response_model=AuthResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Connexion d'un utilisateur
    """
    # Vérifier les credentials
    user = get_user_by_email(db, email=login_data.email)
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte désactivé"
        )
    
    # Définir les scopes selon les rôles
    user_scopes = ["users:read", "products:read", "cart:write", "orders:read"]
    
    for role in user.roles:
        if role.name == "admin":
            user_scopes.extend(["admin", "users:write", "products:write", "orders:write", "media:write", "stories:write"])
        elif role.name == "manager":
            user_scopes.extend(["products:write", "orders:write", "media:write"])
    
    # Créer les tokens
    access_token = create_access_token(
        subject=user.id,
        scopes=user_scopes
    )
    
    refresh_token = create_refresh_token(subject=user.id)
    
    # Sauvegarder le refresh token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, user.id, refresh_token, expires_at)
    
    # Mettre à jour la dernière connexion
    update_last_login(db, user.id)
    
    token_data = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=User.from_orm(user)
    )
    
    return AuthResponse(
        message="Connexion réussie",
        data=token_data
    )


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Rafraîchir un token d'accès
    """
    # Vérifier le refresh token
    db_token = get_refresh_token(db, refresh_data.refresh_token)
    
    if not db_token or not db_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de rafraîchissement invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Récupérer l'utilisateur
    user = db_token.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte désactivé"
        )
    
    # Définir les scopes
    user_scopes = ["users:read", "products:read", "cart:write", "orders:read"]
    
    for role in user.roles:
        if role.name == "admin":
            user_scopes.extend(["admin", "users:write", "products:write", "orders:write", "media:write", "stories:write"])
        elif role.name == "manager":
            user_scopes.extend(["products:write", "orders:write", "media:write"])
    
    # Créer un nouveau token d'accès
    access_token = create_access_token(
        subject=user.id,
        scopes=user_scopes
    )
    
    # Créer un nouveau refresh token et révoquer l'ancien
    new_refresh_token = create_refresh_token(subject=user.id)
    revoke_refresh_token(db, refresh_data.refresh_token)
    
    # Sauvegarder le nouveau refresh token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    save_refresh_token(db, user.id, new_refresh_token, expires_at)
    
    token_data = Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=User.from_orm(user)
    )
    
    return AuthResponse(
        message="Token rafraîchi avec succès",
        data=token_data
    )


@router.post("/logout")
def logout(
    refresh_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Déconnexion - révoque le refresh token
    """
    revoke_refresh_token(db, refresh_data.refresh_token)
    
    return {
        "success": True,
        "message": "Déconnexion réussie"
    }


@router.post("/logout-all")
def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Déconnexion de tous les appareils - révoque tous les refresh tokens
    """
    revoke_all_user_tokens(db, current_user.id)
    
    return {
        "success": True,
        "message": "Déconnexion de tous les appareils réussie"
    }


@router.get("/me", response_model=User)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Récupérer les informations de l'utilisateur connecté
    """
    return current_user


@router.post("/change-password")
def change_password(
    password_data: UserChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Changer le mot de passe de l'utilisateur connecté
    """
    # Vérifier le mot de passe actuel
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )
    
    # Vérifier que le nouveau mot de passe est différent
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit être différent de l'actuel"
        )
    
    # Mettre à jour le mot de passe
    from app.core.security import get_password_hash
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    # Révoquer tous les tokens pour forcer une nouvelle connexion
    revoke_all_user_tokens(db, current_user.id)
    
    return {
        "success": True,
        "message": "Mot de passe changé avec succès"
    }


@router.get("/verify-token")
def verify_token_endpoint(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Vérifier la validité d'un token
    """
    return {
        "success": True,
        "message": "Token valide",
        "user": User.from_orm(current_user)
    }
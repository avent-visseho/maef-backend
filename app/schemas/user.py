# ===================================
# app/schemas/user.py
# ===================================
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta

from app.models.user import User, Role, Permission, RefreshToken
from app.models.address import Address
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Récupérer un utilisateur par son ID avec ses rôles"""
    return db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Récupérer un utilisateur par son email"""
    return db.query(User).options(joinedload(User.roles)).filter(User.email == email.lower()).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Récupérer un utilisateur par son nom d'utilisateur"""
    return db.query(User).options(joinedload(User.roles)).filter(User.username == username).first()


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_name: Optional[str] = None
) -> tuple[List[User], int]:
    """
    Récupérer une liste d'utilisateurs avec filtres
    Retourne (users, total_count)
    """
    query = db.query(User).options(joinedload(User.roles))
    
    # Filtres
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.email).like(search_term),
                func.lower(User.first_name).like(search_term),
                func.lower(User.last_name).like(search_term),
                func.lower(User.username).like(search_term)
            )
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if role_name:
        query = query.join(User.roles).filter(Role.name == role_name)
    
    # Compter le total avant pagination
    total = query.count()
    
    # Appliquer la pagination et trier
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return users, total


def create_user(db: Session, user: UserCreate) -> User:
    """Créer un nouvel utilisateur"""
    hashed_password = get_password_hash(user.password)
    
    db_user = User(
        email=user.email.lower(),
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        password_hash=hashed_password,
        is_active=True,
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Assigner le rôle client par défaut
    customer_role = get_role_by_name(db, "customer")
    if customer_role:
        assign_role_to_user(db, db_user.id, customer_role.id)
    
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Mettre à jour un utilisateur"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    
    # Normaliser l'email
    if "email" in update_data:
        update_data["email"] = update_data["email"].lower()
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Supprimer un utilisateur (soft delete en désactivant)"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db_user.is_active = False
    db.commit()
    return True


def update_last_login(db: Session, user_id: int) -> None:
    """Mettre à jour la date de dernière connexion"""
    db.query(User).filter(User.id == user_id).update(
        {"last_login": datetime.utcnow()}
    )
    db.commit()


# Gestion des rôles
def get_role_by_name(db: Session, role_name: str) -> Optional[Role]:
    """Récupérer un rôle par son nom"""
    return db.query(Role).filter(Role.name == role_name).first()


def get_role_by_id(db: Session, role_id: int) -> Optional[Role]:
    """Récupérer un rôle par son ID"""
    return db.query(Role).filter(Role.id == role_id).first()


def get_all_roles(db: Session) -> List[Role]:
    """Récupérer tous les rôles"""
    return db.query(Role).filter(Role.is_active == True).all()


def create_role(db: Session, name: str, description: str = None) -> Role:
    """Créer un nouveau rôle"""
    db_role = Role(name=name, description=description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def assign_role_to_user(db: Session, user_id: int, role_id: int) -> bool:
    """Assigner un rôle à un utilisateur"""
    user = get_user_by_id(db, user_id)
    role = get_role_by_id(db, role_id)
    
    if not user or not role:
        return False
    
    if role not in user.roles:
        user.roles.append(role)
        db.commit()
    
    return True


def remove_role_from_user(db: Session, user_id: int, role_id: int) -> bool:
    """Retirer un rôle d'un utilisateur"""
    user = get_user_by_id(db, user_id)
    role = get_role_by_id(db, role_id)
    
    if not user or not role:
        return False
    
    if role in user.roles:
        user.roles.remove(role)
        db.commit()
    
    return True


# Gestion des permissions
def get_permission_by_code(db: Session, code: str) -> Optional[Permission]:
    """Récupérer une permission par son code"""
    return db.query(Permission).filter(Permission.code == code).first()


def create_permission(db: Session, code: str, name: str, description: str = None) -> Permission:
    """Créer une nouvelle permission"""
    db_permission = Permission(code=code, name=name, description=description)
    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)
    return db_permission


def assign_permission_to_role(db: Session, role_id: int, permission_id: int) -> bool:
    """Assigner une permission à un rôle"""
    role = get_role_by_id(db, role_id)
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    
    if not role or not permission:
        return False
    
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()
    
    return True


# Gestion des tokens de rafraîchissement
def save_refresh_token(db: Session, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
    """Sauvegarder un token de rafraîchissement"""
    db_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """Récupérer un token de rafraîchissement"""
    return db.query(RefreshToken).filter(
        and_(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
    ).first()


def revoke_refresh_token(db: Session, token: str) -> bool:
    """Révoquer un token de rafraîchissement"""
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db_token.is_revoked = True
        db.commit()
        return True
    return False


def revoke_all_user_tokens(db: Session, user_id: int) -> bool:
    """Révoquer tous les tokens d'un utilisateur"""
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update(
        {"is_revoked": True}
    )
    db.commit()
    return True


def cleanup_expired_tokens(db: Session) -> int:
    """Nettoyer les tokens expirés"""
    expired_count = db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.utcnow()
    ).count()
    
    db.query(RefreshToken).filter(
        RefreshToken.expires_at < datetime.utcnow()
    ).delete()
    
    db.commit()
    return expired_count


# Gestion des adresses
def get_user_addresses(db: Session, user_id: int) -> List[Address]:
    """Récupérer toutes les adresses d'un utilisateur"""
    return db.query(Address).filter(
        and_(Address.user_id == user_id, Address.is_active == True)
    ).order_by(Address.is_default.desc(), Address.created_at.desc()).all()


def get_address_by_id(db: Session, address_id: int, user_id: int) -> Optional[Address]:
    """Récupérer une adresse spécifique d'un utilisateur"""
    return db.query(Address).filter(
        and_(
            Address.id == address_id,
            Address.user_id == user_id,
            Address.is_active == True
        )
    ).first()
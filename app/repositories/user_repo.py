# ===================================
# app/repositories/user_repo.py
# ===================================
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func, and_, or_, desc, update
from datetime import datetime

from app.models.user import User, Role, Permission, RefreshToken
from app.models.address import Address
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Récupérer un utilisateur par son ID"""
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Récupérer un utilisateur par son email"""
    return db.scalar(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))
    )


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Récupérer un utilisateur par son nom d'utilisateur"""
    return db.scalar(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.roles))
    )


def create_user(db: Session, user: UserCreate) -> User:
    """Créer un nouveau utilisateur"""
    hashed_password = get_password_hash(user.password)
    
    db_user = User(
        email=user.email,
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
    
    # Assigner le rôle "customer" par défaut
    customer_role = get_role_by_name(db, "customer")
    if customer_role:
        assign_role_to_user(db, db_user.id, customer_role.id)
    
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Mettre à jour un utilisateur"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Désactiver un utilisateur (soft delete)"""
    user = get_user_by_id(db, user_id)
    if user:
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.commit()
        return True
    return False


def get_users(db: Session, skip: int = 0, limit: int = 100,
              search: Optional[str] = None,
              is_active: Optional[bool] = None,
              role_name: Optional[str] = None) -> Tuple[List[User], int]:
    """Récupérer la liste des utilisateurs avec filtres"""
    query = select(User)
    
    # Filtres
    conditions = []
    
    if search:
        conditions.append(
            or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    
    if role_name:
        conditions.append(User.roles.any(Role.name == role_name))
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Compter le total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query)
    
    # Récupérer avec pagination
    users = db.scalars(
        query.options(selectinload(User.roles))
        .order_by(desc(User.created_at))
        .offset(skip)
        .limit(limit)
    ).all()
    
    return list(users), total or 0


def update_last_login(db: Session, user_id: int):
    """Mettre à jour la dernière connexion"""
    db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login=datetime.utcnow())
    )
    db.commit()


# Gestion des rôles et permissions
def get_all_roles(db: Session) -> List[Role]:
    """Récupérer tous les rôles"""
    return list(db.scalars(
        select(Role)
        .where(Role.is_active == True)
        .order_by(Role.name)
    ))


def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    """Récupérer un rôle par son nom"""
    return db.scalar(select(Role).where(Role.name == name))


def assign_role_to_user(db: Session, user_id: int, role_id: int) -> bool:
    """Assigner un rôle à un utilisateur"""
    user = get_user_by_id(db, user_id)
    role = db.get(Role, role_id)
    
    if user and role and role not in user.roles:
        user.roles.append(role)
        db.commit()
        return True
    return False


def remove_role_from_user(db: Session, user_id: int, role_id: int) -> bool:
    """Retirer un rôle d'un utilisateur"""
    user = get_user_by_id(db, user_id)
    role = db.get(Role, role_id)
    
    if user and role and role in user.roles:
        user.roles.remove(role)
        db.commit()
        return True
    return False


# Gestion des refresh tokens
def save_refresh_token(db: Session, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
    """Sauvegarder un refresh token"""
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
    """Récupérer un refresh token"""
    return db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token == token, RefreshToken.is_revoked == False)
        .options(joinedload(RefreshToken.user))
    )


def revoke_refresh_token(db: Session, token: str) -> bool:
    """Révoquer un refresh token"""
    db_token = db.scalar(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    if db_token:
        db_token.is_revoked = True
        db.commit()
        return True
    return False


def revoke_all_user_tokens(db: Session, user_id: int) -> bool:
    """Révoquer tous les refresh tokens d'un utilisateur"""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .values(is_revoked=True)
    )
    db.commit()
    return True


def cleanup_expired_tokens(db: Session) -> int:
    """Nettoyer les tokens expirés"""
    now = datetime.utcnow()
    result = db.execute(
        update(RefreshToken)
        .where(
            and_(
                RefreshToken.expires_at < now,
                RefreshToken.is_revoked == False
            )
        )
        .values(is_revoked=True)
    )
    db.commit()
    return result.rowcount


# Gestion des adresses
def get_user_addresses(db: Session, user_id: int) -> List[Address]:
    """Récupérer les adresses d'un utilisateur"""
    return list(db.scalars(
        select(Address)
        .where(Address.user_id == user_id, Address.is_active == True)
        .order_by(desc(Address.is_default), desc(Address.created_at))
    ))


def get_address_by_id(db: Session, address_id: int, user_id: Optional[int] = None) -> Optional[Address]:
    """Récupérer une adresse par son ID"""
    query = select(Address).where(Address.id == address_id, Address.is_active == True)
    
    if user_id is not None:
        query = query.where(Address.user_id == user_id)
    
    return db.scalar(query)


def create_default_roles_and_permissions(db: Session):
    """Créer les rôles et permissions par défaut"""
    # Permissions
    permissions_data = [
        {"code": "users:read", "name": "Lire les utilisateurs"},
        {"code": "users:write", "name": "Écrire les utilisateurs"},
        {"code": "products:read", "name": "Lire les produits"},
        {"code": "products:write", "name": "Écrire les produits"},
        {"code": "orders:read", "name": "Lire les commandes"},
        {"code": "orders:write", "name": "Écrire les commandes"},
        {"code": "media:read", "name": "Lire les médias"},
        {"code": "media:write", "name": "Écrire les médias"},
        {"code": "stories:read", "name": "Lire les stories"},
        {"code": "stories:write", "name": "Écrire les stories"},
        {"code": "admin", "name": "Accès administrateur"},
    ]
    
    created_permissions = {}
    for perm_data in permissions_data:
        existing = db.scalar(select(Permission).where(Permission.code == perm_data["code"]))
        if not existing:
            perm = Permission(**perm_data)
            db.add(perm)
            db.flush()
            created_permissions[perm_data["code"]] = perm
        else:
            created_permissions[perm_data["code"]] = existing
    
    # Rôles
    roles_data = [
        {
            "name": "admin",
            "description": "Administrateur avec tous les droits",
            "permissions": ["admin", "users:read", "users:write", "products:read", "products:write", 
                          "orders:read", "orders:write", "media:read", "media:write", "stories:read", "stories:write"]
        },
        {
            "name": "manager",
            "description": "Gestionnaire avec droits limités",
            "permissions": ["products:read", "products:write", "orders:read", "orders:write", "media:read", "media:write"]
        },
        {
            "name": "customer",
            "description": "Client standard",
            "permissions": ["products:read", "orders:read"]
        }
    ]
    
    for role_data in roles_data:
        existing = db.scalar(select(Role).where(Role.name == role_data["name"]))
        if not existing:
            role = Role(name=role_data["name"], description=role_data["description"])
            db.add(role)
            db.flush()
            
            # Assigner les permissions
            for perm_code in role_data["permissions"]:
                if perm_code in created_permissions:
                    role.permissions.append(created_permissions[perm_code])
    
    db.commit()
    print("✓ Rôles et permissions par défaut créés")
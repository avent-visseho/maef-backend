# ===================================
# app/models/user.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base

# Table d'association pour les rôles utilisateur (many-to-many)
user_role_table = Table(
    'user_role',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True)
)

# Table d'association pour les permissions des rôles (many-to-many)
role_permission_table = Table(
    'role_permission',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permission.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    # Authentification
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    roles = relationship("Role", secondary=user_role_table, back_populates="users")
    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    carts = relationship("Cart", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

    @property
    def full_name(self):
        """Nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email

    def has_role(self, role_name: str) -> bool:
        """Vérifier si l'utilisateur a un rôle spécifique"""
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_code: str) -> bool:
        """Vérifier si l'utilisateur a une permission spécifique"""
        for role in self.roles:
            if any(perm.code == permission_code for perm in role.permissions):
                return True
        return False


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)  # admin, manager, customer
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    users = relationship("User", secondary=user_role_table, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permission_table, back_populates="roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # users:read, products:write, etc.
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    roles = relationship("Role", secondary=role_permission_table, back_populates="permissions")

    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}')>"


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    user = relationship("User")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"

    def is_expired(self) -> bool:
        """Vérifier si le token est expiré"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Vérifier si le token est valide (non révoqué et non expiré)"""
        return not self.is_revoked and not self.is_expired()
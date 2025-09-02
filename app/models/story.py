# ===================================
# Fichier: app/models/story.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base

class Story(Base):
    __tablename__ = "story"

    id = Column(Integer, primary_key=True, index=True)
    
    # Plateforme source
    platform = Column(String, nullable=False, index=True)  # 'instagram', 'facebook'
    external_id = Column(String, nullable=False, index=True)  # ID externe unique
    
    # Contenu
    media_type = Column(String, nullable=False)  # 'image', 'video'
    caption = Column(Text, nullable=True)
    permalink = Column(String, nullable=True)
    
    # Média stocké localement
    asset_id = Column(Integer, ForeignKey('media_asset.id'), nullable=True)
    
    # Produit lié (optionnel)
    linked_product_id = Column(Integer, ForeignKey('product.id'), nullable=True)
    
    # Métadonnées
    posted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Pour les stories temporaires
    
    # État
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Statistiques
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    asset = relationship("MediaAsset", back_populates="stories")
    linked_product = relationship("Product")

    def __repr__(self):
        return f"<Story(id={self.id}, platform='{self.platform}', external_id='{self.external_id}')>"

    def is_expired(self) -> bool:
        """Vérifier si la story a expiré"""
        return self.expires_at and datetime.utcnow() > self.expires_at


class OAuthToken(Base):
    """Tokens OAuth pour les intégrations (Instagram, etc.)"""
    __tablename__ = "oauth_token"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)  # 'instagram', 'facebook'
    account_ref = Column(String, nullable=True)  # Référence du compte
    
    # Tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String, default='Bearer')
    
    # Validité
    expires_at = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String, nullable=True)
    
    # État
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<OAuthToken(id={self.id}, provider='{self.provider}')>"

    def is_expired(self) -> bool:
        """Vérifier si le token a expiré"""
        return self.expires_at and datetime.utcnow() > self.expires_at
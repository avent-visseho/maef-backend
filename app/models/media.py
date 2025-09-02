# ===================================
# app/models/media.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from typing import Optional
import hashlib

from app.core.database import Base


class MediaAsset(Base):
    """
    Stockage des fichiers média directement en base de données
    Utilise BYTEA (LargeBinary) pour le stockage des données binaires
    """
    __tablename__ = "media_asset"

    id = Column(Integer, primary_key=True, index=True)
    
    # Hash pour déduplication et vérification d'intégrité
    sha256 = Column(String(64), unique=True, index=True, nullable=False)
    
    # Métadonnées du fichier
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)  # Nom original du fichier uploadé
    mime_type = Column(String, nullable=False, index=True)
    size_bytes = Column(Integer, nullable=False)
    
    # Données binaires du fichier
    data = Column(LargeBinary, nullable=False)
    
    # Métadonnées spécifiques aux images
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Métadonnées spécifiques aux vidéos
    duration_seconds = Column(Integer, nullable=True)
    
    # État et gestion
    is_public = Column(Boolean, default=True)
    is_processed = Column(Boolean, default=False)  # Pour les traitements async
    
    # Métadonnées optionnelles (EXIF, etc.)
    file_metadata = Column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accessed_at = Column(DateTime(timezone=True), nullable=True)  # Dernière consultation
    
    # Relations
    derivatives = relationship("MediaDerivative", back_populates="asset", cascade="all, delete-orphan")
    product_media = relationship("ProductMedia", back_populates="asset")
    stories = relationship("Story", back_populates="asset")

    def __repr__(self):
        return f"<MediaAsset(id={self.id}, filename='{self.filename}', size={self.size_bytes})>"

    @hybrid_property
    def file_extension(self):
        """Extension du fichier"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''

    @hybrid_property
    def is_image(self):
        """Vérifier si c'est une image"""
        return self.mime_type.startswith('image/')

    @hybrid_property
    def is_video(self):
        """Vérifier si c'est une vidéo"""
        return self.mime_type.startswith('video/')

    @hybrid_property
    def size_human(self):
        """Taille du fichier en format lisible"""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @classmethod
    def create_from_bytes(cls, data: bytes, filename: str, mime_type: str, **kwargs):
        """Créer un MediaAsset à partir de données binaires"""
        sha256_hash = hashlib.sha256(data).hexdigest()
        
        return cls(
            data=data,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(data),
            sha256=sha256_hash,
            **kwargs
        )

    def get_derivative(self, kind: str) -> Optional['MediaDerivative']:
        """Récupérer un dérivé spécifique"""
        return next((d for d in self.derivatives if d.kind == kind), None)

    def has_derivative(self, kind: str) -> bool:
        """Vérifier si un dérivé existe"""
        return self.get_derivative(kind) is not None

    def update_access_time(self, db_session):
        """Mettre à jour le timestamp d'accès"""
        from datetime import datetime
        self.accessed_at = datetime.utcnow()
        db_session.commit()


class MediaDerivative(Base):
    """
    Versions dérivées des médias (thumbnails, formats optimisés, etc.)
    """
    __tablename__ = "media_derivative"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey('media_asset.id', ondelete='CASCADE'), nullable=False)
    
    # Type de dérivé
    kind = Column(String, nullable=False, index=True)  # 'thumbnail', 'webp', 'small', 'medium', 'large'
    
    # Métadonnées du fichier dérivé
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    
    # Données binaires du dérivé
    data = Column(LargeBinary, nullable=False)
    
    # Métadonnées spécifiques
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    quality = Column(Integer, nullable=True)  # Qualité de compression (1-100)
    
    # Paramètres de génération
    generation_params = Column(Text, nullable=True)  # JSON des paramètres utilisés
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    asset = relationship("MediaAsset", back_populates="derivatives")

    def __repr__(self):
        return f"<MediaDerivative(id={self.id}, kind='{self.kind}', size={self.size_bytes})>"

    @hybrid_property
    def size_human(self):
        """Taille du fichier en format lisible"""
        size = self.size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @classmethod
    def create_from_bytes(cls, asset_id: int, kind: str, data: bytes, mime_type: str, **kwargs):
        """Créer un MediaDerivative à partir de données binaires"""
        return cls(
            asset_id=asset_id,
            kind=kind,
            data=data,
            mime_type=mime_type,
            size_bytes=len(data),
            **kwargs
        )


# Constantes pour les types de dérivés
class DerivativeKinds:
    THUMBNAIL = "thumbnail"      # 150x150
    SMALL = "small"             # 300x300
    MEDIUM = "medium"           # 600x600
    LARGE = "large"             # 1200x1200
    WEBP_SMALL = "webp_small"   # Version WebP optimisée
    WEBP_MEDIUM = "webp_medium"
    WEBP_LARGE = "webp_large"
    VIDEO_PREVIEW = "video_preview"  # Image de prévisualisation vidéo
    VIDEO_COMPRESSED = "video_compressed"  # Version compressée de la vidéo


# Types MIME supportés
class SupportedMimeTypes:
    # Images
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"
    GIF = "image/gif"
    SVG = "image/svg+xml"
    
    # Vidéos
    MP4 = "video/mp4"
    WEBM = "video/webm"
    MOV = "video/quicktime"
    
    @classmethod
    def is_image(cls, mime_type: str) -> bool:
        return mime_type in [cls.JPEG, cls.PNG, cls.WEBP, cls.GIF, cls.SVG]
    
    @classmethod
    def is_video(cls, mime_type: str) -> bool:
        return mime_type in [cls.MP4, cls.WEBM, cls.MOV]
    
    @classmethod
    def is_supported(cls, mime_type: str) -> bool:
        return cls.is_image(mime_type) or cls.is_video(mime_type)
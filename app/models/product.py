# ===================================
# app/models/product.py
# ===================================
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, 
    Text, DECIMAL, Table, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func as sql_func
from sqlalchemy.ext.hybrid import hybrid_property
from decimal import Decimal

from app.core.database import Base

# Tables d'association
product_category_table = Table(
    'product_category',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('product.id', ondelete='CASCADE'), primary_key=True),
    Column('category_id', Integer, ForeignKey('category.id', ondelete='CASCADE'), primary_key=True)
)

product_tag_table = Table(
    'product_tag',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('product.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    sku_root = Column(String, unique=True, index=True, nullable=False)
    
    # Informations principales
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    brand = Column(String, nullable=True, index=True)
    
    # Spécifications techniques (JSON)
    specs = Column(JSONB, nullable=True)
    
    # État
    is_active = Column(Boolean, default=True, index=True)
    is_featured = Column(Boolean, default=False)
    is_digital = Column(Boolean, default=False)
    requires_shipping = Column(Boolean, default=True)
    
    # SEO
    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    
    # Statistiques
    views_count = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    
    # Poids et dimensions (pour shipping)
    weight_grams = Column(Integer, nullable=True)
    length_cm = Column(Integer, nullable=True)
    width_cm = Column(Integer, nullable=True)
    height_cm = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    prices = relationship("Price", back_populates="product", cascade="all, delete-orphan")
    media = relationship("ProductMedia", back_populates="product", cascade="all, delete-orphan")
    categories = relationship("Category", secondary=product_category_table, back_populates="products")
    tags = relationship("Tag", secondary=product_tag_table, back_populates="products")
    reviews = relationship("Review", back_populates="product")
    inventory = relationship("Inventory", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku_root}', title='{self.title}')>"

    @hybrid_property
    def current_price(self):
        """Prix actuel du produit"""
        from app.models.price import Price
        from datetime import datetime
        
        now = datetime.utcnow()
        for price in self.prices:
            if (price.starts_at <= now and 
                (price.ends_at is None or price.ends_at >= now)):
                return price.amount
        return None

    @hybrid_property
    def average_rating(self):
        """Note moyenne du produit"""
        if not self.reviews:
            return 0
        total = sum(review.rating for review in self.reviews if review.is_approved)
        count = len([r for r in self.reviews if r.is_approved])
        return round(total / count, 1) if count > 0 else 0

    @hybrid_property
    def total_stock(self):
        """Stock total du produit"""
        if self.variants:
            return sum(variant.stock_quantity for variant in self.variants)
        return self.inventory[0].qty_on_hand if self.inventory else 0

    def get_main_image(self):
        """Récupérer l'image principale du produit"""
        main_media = next((m for m in self.media if m.is_primary), None)
        return main_media or (self.media[0] if self.media else None)

    def is_in_stock(self) -> bool:
        """Vérifier si le produit est en stock"""
        return self.total_stock > 0

    def has_variants(self) -> bool:
        """Vérifier si le produit a des variantes"""
        return len(self.variants) > 0


class ProductVariant(Base):
    __tablename__ = "product_variant"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    
    # Informations de la variante
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)  # ex: "Rouge - L"
    
    # Attributs (couleur, taille, etc.)
    attributes = Column(JSONB, nullable=True)  # {"color": "red", "size": "L"}
    
    # État
    is_active = Column(Boolean, default=True)
    
    # Stock
    stock_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    
    # Prix spécifique à la variante (optionnel)
    price_adjustment = Column(DECIMAL(10, 2), default=0)  # Ajustement par rapport au prix de base
    
    # Poids et dimensions spécifiques
    weight_grams = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=sql_func.now())
    
    # Relations
    product = relationship("Product", back_populates="variants")
    prices = relationship("Price", back_populates="variant")
    inventory = relationship("Inventory", back_populates="variant")

    def __repr__(self):
        return f"<ProductVariant(id={self.id}, sku='{self.sku}', name='{self.name}')>"

    @hybrid_property
    def available_quantity(self):
        """Quantité disponible (stock - réservé)"""
        return self.stock_quantity - self.reserved_quantity

    def is_available(self) -> bool:
        """Vérifier si la variante est disponible"""
        return self.is_active and self.available_quantity > 0


class Price(Base):
    __tablename__ = "price"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('product.id', ondelete='CASCADE'), nullable=True)
    variant_id = Column(Integer, ForeignKey('product_variant.id', ondelete='CASCADE'), nullable=True)
    
    # Prix
    currency = Column(String(3), default="XOF", nullable=False)  # ISO 4217
    amount = Column(DECIMAL(10, 2), nullable=False)
    compare_at_amount = Column(DECIMAL(10, 2), nullable=True)  # Prix barré
    
    # Période de validité
    starts_at = Column(DateTime(timezone=True), server_default=sql_func.now(), index=True)
    ends_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # État
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    
    # Relations
    product = relationship("Product", back_populates="prices")
    variant = relationship("ProductVariant", back_populates="prices")

    def __repr__(self):
        return f"<Price(id={self.id}, amount={self.amount} {self.currency})>"

    @hybrid_property
    def is_current(self):
        """Vérifier si ce prix est actuellement valide"""
        from datetime import datetime
        now = datetime.utcnow()
        return (self.is_active and 
                self.starts_at <= now and 
                (self.ends_at is None or self.ends_at >= now))

    @hybrid_property
    def discount_percentage(self):
        """Pourcentage de remise si compare_at_amount est défini"""
        if self.compare_at_amount and self.compare_at_amount > self.amount:
            return round(((self.compare_at_amount - self.amount) / self.compare_at_amount) * 100)
        return 0


class Tag(Base):
    __tablename__ = "tag"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Couleur hex pour l'affichage
    
    # Statistiques
    products_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    
    # Relations
    products = relationship("Product", secondary=product_tag_table, back_populates="tags")

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"


class ProductMedia(Base):
    __tablename__ = "product_media"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    asset_id = Column(Integer, ForeignKey('media_asset.id', ondelete='CASCADE'), nullable=False)
    
    # Paramètres d'affichage
    is_primary = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    alt_text = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now())
    
    # Relations
    product = relationship("Product", back_populates="media")
    asset = relationship("MediaAsset", back_populates="product_media")

    def __repr__(self):
        return f"<ProductMedia(id={self.id}, product_id={self.product_id})>"


# Index pour la recherche full-text (sera créé via migration)
Index('idx_product_fts', Product.id)  # L'index FTS sera créé manuellement
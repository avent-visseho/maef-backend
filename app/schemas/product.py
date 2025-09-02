# ===================================
# app/schemas/product.py
# ===================================

from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    long_description: Optional[str] = None
    brand: Optional[str] = None
    is_featured: bool = False
    is_digital: bool = False
    requires_shipping: bool = True
    weight_grams: Optional[int] = Field(None, ge=0)
    length_cm: Optional[int] = Field(None, ge=0)
    width_cm: Optional[int] = Field(None, ge=0)
    height_cm: Optional[int] = Field(None, ge=0)
    specs: Optional[dict] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class ProductCreate(ProductBase):
    sku_root: str = Field(min_length=1)
    slug: Optional[str] = None  # Généré automatiquement si non fourni
    category_ids: List[int] = []
    tag_ids: List[int] = []
    media_ids: List[int] = []
    price: Decimal = Field(ge=0)
    compare_at_price: Optional[Decimal] = Field(None, ge=0)
    initial_stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    long_description: Optional[str] = None
    brand: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    weight_grams: Optional[int] = None
    specs: Optional[dict] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class ProductVariantBase(BaseModel):
    name: str = Field(min_length=1)
    attributes: Optional[dict] = None
    price_adjustment: Decimal = Field(default=0)
    weight_grams: Optional[int] = None
    initial_stock: int = Field(default=0, ge=0)


class ProductVariantCreate(ProductVariantBase):
    sku: str = Field(min_length=1)


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = None
    attributes: Optional[dict] = None
    price_adjustment: Optional[Decimal] = None
    weight_grams: Optional[int] = None
    is_active: Optional[bool] = None


class ProductVariant(ProductVariantBase):
    id: int
    product_id: int
    sku: str
    is_active: bool
    stock_quantity: int
    available_quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PriceInfo(BaseModel):
    amount: Decimal
    currency: str = "XOF"
    compare_at_amount: Optional[Decimal] = None
    discount_percentage: int = 0
    
    class Config:
        from_attributes = True


class MediaInfo(BaseModel):
    id: int
    asset_id: int
    is_primary: bool
    position: int
    alt_text: Optional[str] = None
    url: str  # URL pour accéder au média
    
    class Config:
        from_attributes = True


class CategoryInfo(BaseModel):
    id: int
    name: str
    slug: str
    
    class Config:
        from_attributes = True


class TagInfo(BaseModel):
    id: int
    name: str
    slug: str
    color: Optional[str] = None
    
    class Config:
        from_attributes = True


class Product(ProductBase):
    id: int
    sku_root: str
    slug: str
    is_active: bool
    views_count: int
    sales_count: int
    created_at: datetime
    published_at: Optional[datetime] = None
    
    # Prix actuel
    current_price: Optional[PriceInfo] = None
    
    # Média principal
    main_image: Optional[MediaInfo] = None
    
    # Stock total
    total_stock: int = 0
    is_in_stock: bool = False
    
    # Note moyenne
    average_rating: float = 0
    
    class Config:
        from_attributes = True


class ProductDetail(Product):
    """Version détaillée avec toutes les relations"""
    variants: List[ProductVariant] = []
    media: List[MediaInfo] = []
    categories: List[CategoryInfo] = []
    tags: List[TagInfo] = []
    related_products: List[Product] = []


class ProductMediaCreate(BaseModel):
    asset_id: int
    is_primary: bool = False
    position: int = 0
    alt_text: Optional[str] = None


class ProductResponse(BaseModel):
    success: bool = True
    message: str
    data: ProductDetail


class ProductsListResponse(BaseModel):
    success: bool = True
    data: List[Product]
    total: int
    page: int
    per_page: int
    has_more: bool


# ===================================
# app/schemas/cart.py
# ===================================
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator


class CartItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(ge=1, description="La quantité doit être positive")


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0, description="Quantité (0 pour supprimer)")


class ProductInfo(BaseModel):
    """Informations simplifiées du produit pour l'affichage du panier"""
    id: int
    title: str
    slug: str
    sku_root: str
    is_active: bool
    
    class Config:
        from_attributes = True


class ProductVariantInfo(BaseModel):
    """Informations simplifiées de la variante pour l'affichage du panier"""
    id: int
    name: str
    sku: str
    attributes: Optional[dict] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class CartItem(CartItemBase):
    id: int
    cart_id: int
    unit_price: Optional[Decimal] = None
    currency: str = "XOF"
    line_total: Decimal
    display_name: str
    current_unit_price: Decimal
    available_stock: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Relations
    product: ProductInfo
    variant: Optional[ProductVariantInfo] = None
    
    class Config:
        from_attributes = True


class CartBase(BaseModel):
    currency: str = Field(default="XOF", max_length=3)
    notes: Optional[str] = None


class Cart(CartBase):
    id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Propriétés calculées
    items_count: int
    unique_items_count: int
    subtotal: Decimal
    total_weight_grams: Optional[int] = None
    
    # Relations
    items: List[CartItem] = []
    
    class Config:
        from_attributes = True
    
    @validator('items_count', pre=True, always=True)
    def calculate_items_count(cls, v, values):
        if 'items' in values:
            return sum(item.quantity for item in values['items'])
        return v or 0
    
    @validator('unique_items_count', pre=True, always=True)  
    def calculate_unique_items_count(cls, v, values):
        if 'items' in values:
            return len(values['items'])
        return v or 0
    
    @validator('subtotal', pre=True, always=True)
    def calculate_subtotal(cls, v, values):
        if 'items' in values:
            return sum(item.line_total for item in values['items'])
        return v or Decimal('0')


class CartSummary(BaseModel):
    """Résumé du panier pour l'affichage rapide"""
    items_count: int
    unique_items_count: int
    subtotal: Decimal
    currency: str = "XOF"


class CartResponse(BaseModel):
    success: bool = True
    message: str
    data: Cart


class CartValidationResponse(BaseModel):
    success: bool = True
    message: str
    data: Cart
    is_valid: bool
    errors: List[str] = []


class CartStatsResponse(BaseModel):
    success: bool = True
    message: str
    data: dict
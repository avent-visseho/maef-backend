# ===================================
# app/schemas/order.py
# ===================================
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.order import OrderStatus, PaymentStatus, ShipmentStatus


# Enums pour l'API
class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RETURNED = "returned"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class ShipmentStatusEnum(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED = "returned"


# Schémas de base
class OrderItemBase(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(ge=1, description="Quantité doit être positive")
    

class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: int
    unit_price: Decimal = Field(ge=0)
    currency: str = Field(default="XOF", max_length=3)
    product_title: str
    product_sku: str
    variant_name: Optional[str] = None
    discount_amount: Decimal = Field(default=0, ge=0)
    quantity_fulfilled: int = Field(default=0, ge=0)
    line_total: Decimal
    display_name: str
    fulfillment_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AddressInfo(BaseModel):
    """Adresse simplifiée pour les commandes"""
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: str
    zip_code: str


class OrderBase(BaseModel):
    guest_email: Optional[str] = None
    notes: Optional[str] = None
    shipping_method: Optional[str] = None
    

class OrderCreate(OrderBase):
    billing_address: AddressInfo
    shipping_address: Optional[AddressInfo] = None


class Order(OrderBase):
    id: int
    order_number: str
    user_id: Optional[int] = None
    status: OrderStatusEnum
    payment_status: PaymentStatusEnum
    fulfillment_status: str
    currency: str = "XOF"
    subtotal: Decimal = Field(ge=0)
    discount_total: Decimal = Field(ge=0)
    shipping_total: Decimal = Field(ge=0)
    tax_total: Decimal = Field(ge=0)
    grand_total: Decimal = Field(ge=0)
    billing_address: Optional[AddressInfo] = None
    shipping_address: Optional[AddressInfo] = None
    items_count: int = 0
    unique_items_count: int = 0
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Relations
    items: List[OrderItem] = []
    
    class Config:
        from_attributes = True


class OrderDetail(Order):
    """Version détaillée avec toutes les relations"""
    user: Optional[dict] = None  # Infos utilisateur simplifiées
    shipments: List[dict] = []
    payments: List[dict] = []


class OrderResponse(BaseModel):
    success: bool = True
    message: str
    data: Order


class OrdersListResponse(BaseModel):
    success: bool = True
    data: List[Order]
    total: int
    page: int
    per_page: int
    has_more: bool


class OrderStatsResponse(BaseModel):
    success: bool = True
    message: str
    data: dict


# Schémas pour les expéditions
class ShipmentBase(BaseModel):
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    service: Optional[str] = None
    notes: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    order_items: List[dict] = []  # [{"order_item_id": 1, "quantity": 2}]


class Shipment(ShipmentBase):
    id: int
    order_id: int
    status: ShipmentStatusEnum
    weight_grams: Optional[int] = None
    shipping_cost: Optional[Decimal] = None
    created_at: datetime
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
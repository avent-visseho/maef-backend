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
    shipping_address: Optional[
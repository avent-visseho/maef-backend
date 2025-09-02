# ===================================
# Fichier: app/models/promotion.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, DECIMAL, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from decimal import Decimal
import enum

from app.core.database import Base

class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_SHIPPING = "free_shipping"

class Coupon(Base):
    __tablename__ = "coupon"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    
    # Type et valeur de la remise
    discount_type = Column(String, nullable=False)  # DiscountType
    discount_value = Column(DECIMAL(10, 2), nullable=False)
    
    # Conditions d'utilisation
    minimum_amount = Column(DECIMAL(10, 2), nullable=True)  # Montant minimum
    maximum_discount = Column(DECIMAL(10, 2), nullable=True)  # Remise maximum
    
    # Limites d'utilisation
    usage_limit = Column(Integer, nullable=True)  # Limite globale
    usage_limit_per_user = Column(Integer, nullable=True)  # Limite par utilisateur
    used_count = Column(Integer, default=0)
    
    # Validité
    starts_at = Column(DateTime(timezone=True), server_default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # État
    is_active = Column(Boolean, default=True)
    
    # Restrictions (JSON)
    restrictions = Column(JSONB, nullable=True)  # Catégories, produits exclus, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Coupon(id={self.id}, code='{self.code}')>"

    def is_valid(self) -> bool:
        """Vérifier si le coupon est valide"""
        from datetime import datetime
        now = datetime.utcnow()
        
        return (self.is_active and 
                self.starts_at <= now and
                (self.ends_at is None or self.ends_at >= now) and
                (self.usage_limit is None or self.used_count < self.usage_limit))

    def calculate_discount(self, amount: Decimal) -> Decimal:
        """Calculer le montant de la remise"""
        if not self.is_valid():
            return Decimal('0')
        
        if self.minimum_amount and amount < self.minimum_amount:
            return Decimal('0')
        
        if self.discount_type == DiscountType.PERCENTAGE:
            discount = amount * (self.discount_value / 100)
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            discount = self.discount_value
        else:  # FREE_SHIPPING
            return Decimal('0')  # Géré ailleurs
        
        if self.maximum_discount and discount > self.maximum_discount:
            discount = self.maximum_discount
        
        return min(discount, amount)
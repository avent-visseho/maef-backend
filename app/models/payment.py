# ===================================
# Fichier: app/models/payment.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import enum

from app.core.database import Base

class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    FEDAPAY = "fedapay"
    PAYSTACK = "paystack"
    PAYPAL = "paypal"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    
    # Provider de paiement
    provider = Column(String, nullable=False)  # PaymentProvider
    provider_payment_id = Column(String, nullable=True, index=True)  # ID chez le provider
    
    # Montant
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="XOF", nullable=False)
    
    # Statut
    status = Column(String, default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Méthode de paiement
    payment_method = Column(String, nullable=True)  # 'card', 'mobile_money', etc.
    
    # Métadonnées du provider
    provider_response = Column(Text, nullable=True)  # JSON de la réponse
    failure_reason = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    succeeded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    order = relationship("Order", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, order_id={self.order_id}, status='{self.status}')>"

    def is_successful(self) -> bool:
        """Vérifier si le paiement est réussi"""
        return self.status == PaymentStatus.SUCCEEDED


class Refund(Base):
    __tablename__ = "refund"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey('payment.id', ondelete='CASCADE'), nullable=False)
    
    # Montant remboursé
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="XOF", nullable=False)
    
    # Raison
    reason = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Provider
    provider_refund_id = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    payment = relationship("Payment")

    def __repr__(self):
        return f"<Refund(id={self.id}, payment_id={self.payment_id}, amount={self.amount})>"
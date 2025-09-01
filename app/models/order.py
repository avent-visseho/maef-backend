# ===================================
# app/models/order.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from decimal import Decimal
from datetime import datetime
import enum
from typing import List, Optional

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    """Statuts de commande"""
    PENDING = "pending"           # En attente de paiement
    CONFIRMED = "confirmed"       # Confirmée et payée
    PROCESSING = "processing"     # En cours de préparation
    SHIPPED = "shipped"          # Expédiée
    DELIVERED = "delivered"      # Livrée
    CANCELLED = "cancelled"      # Annulée
    REFUNDED = "refunded"        # Remboursée
    RETURNED = "returned"        # Retournée


class PaymentStatus(str, enum.Enum):
    """Statuts de paiement"""
    PENDING = "pending"          # En attente
    PROCESSING = "processing"    # En cours de traitement
    PAID = "paid"               # Payé
    FAILED = "failed"           # Échoué
    CANCELLED = "cancelled"     # Annulé
    REFUNDED = "refunded"       # Remboursé
    PARTIAL_REFUND = "partial_refund"  # Remboursement partiel


class ShipmentStatus(str, enum.Enum):
    """Statuts d'expédition"""
    PENDING = "pending"          # En attente
    PREPARING = "preparing"      # En préparation
    SHIPPED = "shipped"          # Expédié
    IN_TRANSIT = "in_transit"    # En transit
    OUT_FOR_DELIVERY = "out_for_delivery"  # En cours de livraison
    DELIVERED = "delivered"      # Livré
    FAILED_DELIVERY = "failed_delivery"    # Échec de livraison
    RETURNED = "returned"        # Retourné


class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)  # Ex: "ORD-2024-000001"
    
    # Client
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    guest_email = Column(String, nullable=True)  # Pour les commandes invités
    
    # Statuts
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    fulfillment_status = Column(String, default="unfulfilled", nullable=False)  # unfulfilled, partial, fulfilled
    
    # Montants (en centimes pour éviter les problèmes de précision)
    currency = Column(String(3), default="XOF", nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)              # Sous-total des articles
    discount_total = Column(DECIMAL(10, 2), default=0, nullable=False)  # Remises appliquées
    shipping_total = Column(DECIMAL(10, 2), default=0, nullable=False)  # Frais de livraison
    tax_total = Column(DECIMAL(10, 2), default=0, nullable=False)       # Taxes
    grand_total = Column(DECIMAL(10, 2), nullable=False)               # Total final
    
    # Informations de facturation
    billing_address = Column(Text, nullable=True)  # JSON de l'adresse de facturation
    
    # Informations de livraison
    shipping_address = Column(Text, nullable=True)  # JSON de l'adresse de livraison
    shipping_method = Column(String, nullable=True)  # Méthode de livraison choisie
    
    # Notes et commentaires
    notes = Column(Text, nullable=True)  # Notes du client
    internal_notes = Column(Text, nullable=True)  # Notes internes (admin)
    
    # Tracking et références
    source = Column(String, nullable=True)  # web, mobile, admin, etc.
    referrer = Column(String, nullable=True)  # URL de référence
    
    # Codes promotionnels utilisés
    discount_codes = Column(Text, nullable=True)  # JSON des codes utilisés
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="order", cascade="all, delete-orphan")
    # refunds = relationship("Refund", back_populates="order")

    def __repr__(self):
        return f"<Order(id={self.id}, number='{self.order_number}', status='{self.status}')>"

    @hybrid_property
    def is_paid(self):
        """Vérifier si la commande est payée"""
        return self.payment_status == PaymentStatus.PAID

    @hybrid_property
    def is_completed(self):
        """Vérifier si la commande est complètement terminée"""
        return self.status == OrderStatus.DELIVERED

    @hybrid_property
    def can_be_cancelled(self):
        """Vérifier si la commande peut être annulée"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]

    @hybrid_property
    def total_items_count(self):
        """Nombre total d'articles dans la commande"""
        return sum(item.quantity for item in self.items)

    @hybrid_property
    def unique_items_count(self):
        """Nombre d'articles uniques dans la commande"""
        return len(self.items)

    @hybrid_property
    def total_weight_grams(self):
        """Poids total de la commande"""
        total = 0
        for item in self.items:
            weight = 0
            if item.variant and item.variant.weight_grams:
                weight = item.variant.weight_grams
            elif item.product and item.product.weight_grams:
                weight = item.product.weight_grams
            total += weight * item.quantity
        return total

    def calculate_totals(self):
        """Recalculer tous les totaux de la commande"""
        # Sous-total des articles
        self.subtotal = sum(item.line_total for item in self.items)
        
        # Le grand total sera calculé avec les remises, taxes et frais de port
        # TODO: Intégrer le service de pricing pour les calculs avancés
        self.grand_total = self.subtotal - self.discount_total + self.shipping_total + self.tax_total

    def add_item(self, product_id: int, quantity: int, unit_price: Decimal, 
                 variant_id: Optional[int] = None, **kwargs) -> 'OrderItem':
        """Ajouter un article à la commande"""
        item = OrderItem(
            order_id=self.id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            currency=self.currency,
            **kwargs
        )
        self.items.append(item)
        self.calculate_totals()
        return item

    def update_status(self, new_status: OrderStatus, notes: str = None):
        """Mettre à jour le statut de la commande avec horodatage"""
        old_status = self.status
        self.status = new_status
        
        # Mettre à jour les timestamps selon le statut
        now = datetime.utcnow()
        if new_status == OrderStatus.CONFIRMED:
            self.confirmed_at = now
        elif new_status == OrderStatus.SHIPPED:
            self.shipped_at = now
        elif new_status == OrderStatus.DELIVERED:
            self.delivered_at = now
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = now
        
        # Ajouter une note interne
        if notes:
            self.internal_notes = f"{self.internal_notes or ''}\n[{now}] {old_status} -> {new_status}: {notes}"

    @classmethod
    def generate_order_number(cls, db_session) -> str:
        """Générer un numéro de commande unique"""
        from sqlalchemy import func as sql_func, extract
        
        # Compter les commandes de cette année
        current_year = datetime.utcnow().year
        count = db_session.query(sql_func.count(cls.id)).filter(
            extract('year', cls.created_at) == current_year
        ).scalar() or 0
        
        return f"ORD-{current_year}-{(count + 1):06d}"

    def to_dict(self):
        """Convertir en dictionnaire pour l'API"""
        return {
            "id": self.id,
            "order_number": self.order_number,
            "status": self.status,
            "payment_status": self.payment_status,
            "currency": self.currency,
            "subtotal": float(self.subtotal),
            "discount_total": float(self.discount_total),
            "shipping_total": float(self.shipping_total),
            "tax_total": float(self.tax_total),
            "grand_total": float(self.grand_total),
            "items_count": self.total_items_count,
            "created_at": self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }


class OrderItem(Base):
    __tablename__ = "order_item"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id', ondelete='RESTRICT'), nullable=False)
    variant_id = Column(Integer, ForeignKey('product_variant.id', ondelete='RESTRICT'), nullable=True)
    
    # Quantité commandée
    quantity = Column(Integer, nullable=False)
    quantity_fulfilled = Column(Integer, default=0, nullable=False)  # Quantité expédiée/livrée
    
    # Prix au moment de la commande (important pour l'historique)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="XOF", nullable=False)
    
    # Informations du produit au moment de la commande (pour l'historique)
    product_title = Column(String, nullable=False)
    product_sku = Column(String, nullable=False)
    variant_name = Column(String, nullable=True)
    
    # Remises spécifiques à cet article
    discount_amount = Column(DECIMAL(10, 2), default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, product='{self.product_title}', qty={self.quantity})>"

    @hybrid_property
    def line_total(self):
        """Total de la ligne (quantité × prix unitaire - remise)"""
        return (self.unit_price * self.quantity) - self.discount_amount

    @hybrid_property
    def display_name(self):
        """Nom d'affichage de l'article"""
        name = self.product_title
        if self.variant_name:
            name += f" - {self.variant_name}"
        return name

    @hybrid_property
    def fulfillment_status(self):
        """Statut d'expédition de cet article"""
        if self.quantity_fulfilled == 0:
            return "unfulfilled"
        elif self.quantity_fulfilled < self.quantity:
            return "partial"
        else:
            return "fulfilled"

    @hybrid_property
    def quantity_remaining(self):
        """Quantité restant à expédier"""
        return self.quantity - self.quantity_fulfilled

    def fulfill(self, quantity: int) -> bool:
        """Marquer une quantité comme expédiée"""
        if quantity <= self.quantity_remaining:
            self.quantity_fulfilled += quantity
            return True
        return False


class Shipment(Base):
    __tablename__ = "shipment"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('order.id', ondelete='CASCADE'), nullable=False)
    
    # Informations d'expédition
    tracking_number = Column(String, index=True, nullable=True)
    carrier = Column(String, nullable=True)  # DHL, Chronopost, etc.
    service = Column(String, nullable=True)  # Express, Standard, etc.
    
    # Statut
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False, index=True)
    
    # Adresse de livraison (copie au moment de l'expédition)
    shipping_address = Column(Text, nullable=True)  # JSON
    
    # Poids et dimensions
    weight_grams = Column(Integer, nullable=True)
    length_cm = Column(Integer, nullable=True)
    width_cm = Column(Integer, nullable=True)
    height_cm = Column(Integer, nullable=True)
    
    # Coûts
    shipping_cost = Column(DECIMAL(10, 2), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    estimated_delivery_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    order = relationship("Order", back_populates="shipments")
    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Shipment(id={self.id}, order_id={self.order_id}, status='{self.status}')>"

    @hybrid_property
    def is_delivered(self):
        """Vérifier si l'expédition est livrée"""
        return self.status == ShipmentStatus.DELIVERED

    @hybrid_property
    def total_items_count(self):
        """Nombre total d'articles dans cette expédition"""
        return sum(item.quantity for item in self.items)

    def add_item(self, order_item_id: int, quantity: int):
        """Ajouter un article à cette expédition"""
        shipment_item = ShipmentItem(
            shipment_id=self.id,
            order_item_id=order_item_id,
            quantity=quantity
        )
        self.items.append(shipment_item)
        return shipment_item

    def update_status(self, new_status: ShipmentStatus):
        """Mettre à jour le statut d'expédition avec horodatage"""
        self.status = new_status
        
        now = datetime.utcnow()
        if new_status == ShipmentStatus.SHIPPED:
            self.shipped_at = now
        elif new_status == ShipmentStatus.DELIVERED:
            self.delivered_at = now


class ShipmentItem(Base):
    __tablename__ = "shipment_item"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey('shipment.id', ondelete='CASCADE'), nullable=False)
    order_item_id = Column(Integer, ForeignKey('order_item.id', ondelete='CASCADE'), nullable=False)
    
    # Quantité expédiée (peut être partielle)
    quantity = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    shipment = relationship("Shipment", back_populates="items")
    order_item = relationship("OrderItem")

    def __repr__(self):
        return f"<ShipmentItem(id={self.id}, qty={self.quantity})>"
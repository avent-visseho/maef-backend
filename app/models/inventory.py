# ===================================
# app/models/inventory.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from typing import List, Optional
from enum import Enum

from app.core.database import Base


class StockMovementType(str, Enum):
    """Types de mouvements de stock"""
    RESTOCK = "restock"           # Réapprovisionnement
    SALE = "sale"                 # Vente
    RETURN = "return"             # Retour
    DAMAGED = "damaged"           # Produit endommagé
    ADJUSTMENT = "adjustment"     # Ajustement manuel
    RESERVED = "reserved"         # Réservation
    UNRESERVED = "unreserved"     # Libération de réservation
    TRANSFER = "transfer"         # Transfert entre entrepôts


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint('qty_on_hand >= 0', name='check_qty_on_hand_positive'),
        CheckConstraint('qty_reserved >= 0', name='check_qty_reserved_positive'),
        CheckConstraint('qty_reserved <= qty_on_hand', name='check_reserved_le_on_hand'),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Référence au produit ou variante
    product_id = Column(Integer, ForeignKey('product.id', ondelete='CASCADE'), nullable=True)
    variant_id = Column(Integer, ForeignKey('product_variant.id', ondelete='CASCADE'), nullable=True)
    
    # Localisation (optionnel pour multi-entrepôts)
    location = Column(String, default="main", nullable=False, index=True)
    
    # Quantités
    qty_on_hand = Column(Integer, default=0, nullable=False)      # Stock physique
    qty_reserved = Column(Integer, default=0, nullable=False)     # Stock réservé (commandes en cours)
    qty_committed = Column(Integer, default=0, nullable=False)    # Stock engagé (en préparation)
    
    # Seuils d'alerte
    low_stock_threshold = Column(Integer, default=5, nullable=False)
    critical_stock_threshold = Column(Integer, default=1, nullable=False)
    
    # Coûts (pour valorisation du stock)
    unit_cost = Column(Integer, nullable=True)  # Coût unitaire en centimes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_movement_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    product = relationship("Product", back_populates="inventory")
    variant = relationship("ProductVariant", back_populates="inventory")
    movements = relationship("StockMovement", back_populates="inventory", cascade="all, delete-orphan")
    reservations = relationship("StockReservation", back_populates="inventory", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Inventory(id={self.id}, product_id={self.product_id}, qty={self.qty_available})>"

    @hybrid_property
    def qty_available(self):
        """Quantité disponible à la vente (stock - réservé - engagé)"""
        return self.qty_on_hand - self.qty_reserved - self.qty_committed

    @hybrid_property
    def is_low_stock(self):
        """Vérifier si le stock est bas"""
        return self.qty_available <= self.low_stock_threshold

    @hybrid_property
    def is_critical_stock(self):
        """Vérifier si le stock est critique"""
        return self.qty_available <= self.critical_stock_threshold

    @hybrid_property
    def is_out_of_stock(self):
        """Vérifier si en rupture de stock"""
        return self.qty_available <= 0

    @hybrid_property
    def stock_status(self):
        """Statut du stock"""
        if self.is_out_of_stock:
            return "out_of_stock"
        elif self.is_critical_stock:
            return "critical"
        elif self.is_low_stock:
            return "low"
        return "available"

    @hybrid_property
    def total_value(self):
        """Valeur totale du stock"""
        if self.unit_cost:
            return (self.qty_on_hand * self.unit_cost) / 100  # Convertir centimes en euros/XOF
        return 0

    def can_fulfill(self, quantity: int) -> bool:
        """Vérifier si on peut satisfaire une demande de quantité donnée"""
        return self.qty_available >= quantity

    def adjust_stock(self, quantity_change: int, movement_type: StockMovementType, 
                     reason: str = None, reference: str = None, db_session = None):
        """Ajuster le stock avec création d'un mouvement"""
        old_qty = self.qty_on_hand
        self.qty_on_hand += quantity_change
        
        # Créer le mouvement de stock
        movement = StockMovement(
            inventory_id=self.id,
            movement_type=movement_type,
            quantity=quantity_change,
            quantity_before=old_qty,
            quantity_after=self.qty_on_hand,
            reason=reason,
            reference=reference
        )
        
        if db_session:
            db_session.add(movement)
            self.last_movement_at = datetime.utcnow()

    def reserve_stock(self, quantity: int, reference: str = None, expires_at: datetime = None, 
                      db_session = None) -> Optional['StockReservation']:
        """Réserver du stock"""
        if not self.can_fulfill(quantity):
            return None
        
        self.qty_reserved += quantity
        
        reservation = StockReservation(
            inventory_id=self.id,
            quantity=quantity,
            reference=reference,
            expires_at=expires_at
        )
        
        if db_session:
            db_session.add(reservation)
            self.adjust_stock(0, StockMovementType.RESERVED, f"Réservation de {quantity} unités", reference, db_session)
        
        return reservation

    def unreserve_stock(self, reservation: 'StockReservation', db_session = None):
        """Libérer une réservation de stock"""
        if reservation.is_active:
            self.qty_reserved -= reservation.quantity
            reservation.is_active = False
            reservation.released_at = datetime.utcnow()
            
            if db_session:
                self.adjust_stock(0, StockMovementType.UNRESERVED, 
                                f"Libération de {reservation.quantity} unités", 
                                reservation.reference, db_session)

    def fulfill_reservation(self, reservation: 'StockReservation', db_session = None):
        """Exécuter une réservation (vendre le stock réservé)"""
        if reservation.is_active:
            self.qty_reserved -= reservation.quantity
            self.qty_on_hand -= reservation.quantity
            reservation.is_active = False
            reservation.fulfilled_at = datetime.utcnow()
            
            if db_session:
                self.adjust_stock(-reservation.quantity, StockMovementType.SALE,
                                f"Vente de {reservation.quantity} unités",
                                reservation.reference, db_session)


class StockMovement(Base):
    """Historique des mouvements de stock"""
    __tablename__ = "stock_movement"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False)
    
    # Type de mouvement
    movement_type = Column(String, nullable=False, index=True)  # StockMovementType
    
    # Quantités
    quantity = Column(Integer, nullable=False)  # Quantité du mouvement (+/-)
    quantity_before = Column(Integer, nullable=False)  # Stock avant mouvement
    quantity_after = Column(Integer, nullable=False)   # Stock après mouvement
    
    # Métadonnées
    reason = Column(Text, nullable=True)  # Raison du mouvement
    reference = Column(String, nullable=True)  # Référence externe (commande, bon de livraison, etc.)
    
    # Coût du mouvement (optionnel)
    unit_cost = Column(Integer, nullable=True)  # Coût unitaire en centimes
    total_cost = Column(Integer, nullable=True)  # Coût total en centimes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relations
    inventory = relationship("Inventory", back_populates="movements")

    def __repr__(self):
        return f"<StockMovement(id={self.id}, type='{self.movement_type}', qty={self.quantity})>"

    @hybrid_property
    def is_inbound(self):
        """Mouvement entrant (augmente le stock)"""
        return self.quantity > 0

    @hybrid_property
    def is_outbound(self):
        """Mouvement sortant (diminue le stock)"""
        return self.quantity < 0


class StockReservation(Base):
    """Réservations de stock"""
    __tablename__ = "stock_reservation"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey('inventory.id', ondelete='CASCADE'), nullable=False)
    
    # Quantité réservée
    quantity = Column(Integer, nullable=False)
    
    # Référence externe (commande, panier, etc.)
    reference = Column(String, nullable=True, index=True)
    
    # État
    is_active = Column(Boolean, default=True)
    
    # Expiration de la réservation
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at = Column(DateTime(timezone=True), nullable=True)
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    inventory = relationship("Inventory", back_populates="reservations")

    def __repr__(self):
        return f"<StockReservation(id={self.id}, qty={self.quantity}, active={self.is_active})>"

    @hybrid_property
    def is_expired(self):
        """Vérifier si la réservation a expiré"""
        return self.expires_at and datetime.utcnow() > self.expires_at

    def should_be_released(self):
        """Vérifier si la réservation devrait être libérée"""
        return self.is_active and self.is_expired
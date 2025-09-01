# ===================================
# app/models/cart.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from decimal import Decimal
from typing import List, Optional

from app.core.database import Base


class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identification du panier
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)  # Pour les utilisateurs non connectés
    
    # Devise du panier
    currency = Column(String(3), default="XOF", nullable=False)
    
    # Métadonnées
    notes = Column(Text, nullable=True)  # Notes du client
    
    # État
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id}, items_count={len(self.items)})>"

    @hybrid_property
    def items_count(self):
        """Nombre total d'articles dans le panier"""
        return sum(item.quantity for item in self.items)

    @hybrid_property
    def unique_items_count(self):
        """Nombre d'articles uniques dans le panier"""
        return len(self.items)

    @hybrid_property
    def subtotal(self):
        """Sous-total du panier"""
        return sum(item.line_total for item in self.items)

    @hybrid_property
    def total_weight_grams(self):
        """Poids total du panier en grammes"""
        total = 0
        for item in self.items:
            if item.variant and item.variant.weight_grams:
                total += item.variant.weight_grams * item.quantity
            elif item.product.weight_grams:
                total += item.product.weight_grams * item.quantity
        return total

    def is_empty(self) -> bool:
        """Vérifier si le panier est vide"""
        return len(self.items) == 0

    def add_item(self, product_id: int, quantity: int = 1, variant_id: Optional[int] = None) -> 'CartItem':
        """Ajouter un article au panier ou augmenter la quantité"""
        # Chercher si l'article existe déjà
        existing_item = next(
            (item for item in self.items 
             if item.product_id == product_id and item.variant_id == variant_id),
            None
        )
        
        if existing_item:
            existing_item.quantity += quantity
            return existing_item
        else:
            # Créer un nouveau CartItem
            new_item = CartItem(
                cart_id=self.id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity
            )
            self.items.append(new_item)
            return new_item

    def update_item_quantity(self, item_id: int, quantity: int) -> bool:
        """Mettre à jour la quantité d'un article"""
        item = next((item for item in self.items if item.id == item_id), None)
        if item:
            if quantity <= 0:
                self.items.remove(item)
            else:
                item.quantity = quantity
            return True
        return False

    def remove_item(self, item_id: int) -> bool:
        """Supprimer un article du panier"""
        item = next((item for item in self.items if item.id == item_id), None)
        if item:
            self.items.remove(item)
            return True
        return False

    def clear(self):
        """Vider le panier"""
        self.items.clear()

    def validate_items(self, db_session) -> List[str]:
        """Valider tous les articles du panier et retourner les erreurs"""
        errors = []
        items_to_remove = []
        
        for item in self.items:
            item_errors = item.validate(db_session)
            if item_errors:
                errors.extend([f"Article {item.id}: {error}" for error in item_errors])
                # Si le produit n'existe plus, le supprimer du panier
                if "n'existe plus" in ' '.join(item_errors):
                    items_to_remove.append(item)
        
        # Supprimer les articles invalides
        for item in items_to_remove:
            self.items.remove(item)
        
        return errors


class CartItem(Base):
    __tablename__ = "cart_item"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('cart.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    variant_id = Column(Integer, ForeignKey('product_variant.id', ondelete='CASCADE'), nullable=True)
    
    # Quantité
    quantity = Column(Integer, nullable=False, default=1)
    
    # Prix au moment de l'ajout (pour préserver l'historique)
    unit_price = Column(DECIMAL(10, 2), nullable=True)
    currency = Column(String(3), default="XOF", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    def __repr__(self):
        return f"<CartItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"

    @hybrid_property
    def current_unit_price(self):
        """Prix unitaire actuel du produit/variante"""
        if self.variant:
            # Prix de la variante si elle en a un spécifique
            variant_price = next((p for p in self.variant.prices if p.is_current), None)
            if variant_price:
                return variant_price.amount
        
        # Prix du produit
        product_price = next((p for p in self.product.prices if p.is_current), None)
        if product_price:
            base_price = product_price.amount
            # Ajouter l'ajustement de la variante si applicable
            if self.variant and self.variant.price_adjustment:
                base_price += self.variant.price_adjustment
            return base_price
        
        return Decimal('0')

    @hybrid_property
    def line_total(self):
        """Total de la ligne (quantité × prix unitaire)"""
        price = self.unit_price or self.current_unit_price
        return price * self.quantity if price else Decimal('0')

    @hybrid_property
    def display_name(self):
        """Nom d'affichage de l'article"""
        name = self.product.title
        if self.variant:
            name += f" - {self.variant.name}"
        return name

    @hybrid_property
    def available_stock(self):
        """Stock disponible pour cet article"""
        if self.variant:
            return self.variant.available_quantity
        elif self.product.inventory:
            return self.product.inventory[0].qty_on_hand - self.product.inventory[0].qty_reserved
        return 0

    def validate(self, db_session) -> List[str]:
        """Valider cet article du panier"""
        errors = []
        
        # Vérifier que le produit existe et est actif
        if not self.product or not self.product.is_active:
            errors.append("Le produit n'existe plus ou n'est plus disponible")
            return errors
        
        # Vérifier que la variante existe et est active (si applicable)
        if self.variant_id:
            if not self.variant or not self.variant.is_active:
                errors.append("La variante sélectionnée n'est plus disponible")
                return errors
        
        # Vérifier le stock
        available = self.available_stock
        if available <= 0:
            errors.append("Plus en stock")
        elif self.quantity > available:
            errors.append(f"Stock insuffisant (disponible: {available})")
        
        # Vérifier le prix
        current_price = self.current_unit_price
        if current_price <= 0:
            errors.append("Prix non disponible")
        
        return errors

    def update_price(self):
        """Mettre à jour le prix stocké avec le prix actuel"""
        self.unit_price = self.current_unit_price
        self.currency = "XOF"  # ou récupérer depuis les settings

    def is_valid(self) -> bool:
        """Vérifier si l'article est valide"""
        return len(self.validate(None)) == 0  # Note: nécessite une session DB pour validation complète
# ===================================
# app/repositories/cart_repo.py
# ===================================
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta

from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import User


class CartRepository:
    """Repository pour la gestion des paniers"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_cart_by_id(self, cart_id: int) -> Optional[Cart]:
        """Récupérer un panier par son ID"""
        return self.db.scalar(
            select(Cart)
            .where(Cart.id == cart_id, Cart.is_active == True)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product),
                selectinload(Cart.items).selectinload(CartItem.variant),
                selectinload(Cart.user)
            )
        )

    def get_user_cart(self, user_id: int) -> Optional[Cart]:
        """Récupérer le panier actif d'un utilisateur"""
        return self.db.scalar(
            select(Cart)
            .where(Cart.user_id == user_id, Cart.is_active == True)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product),
                selectinload(Cart.items).selectinload(CartItem.variant)
            )
        )

    def get_cart_by_session_id(self, session_id: str) -> Optional[Cart]:
        """Récupérer un panier par session ID (utilisateurs non connectés)"""
        return self.db.scalar(
            select(Cart)
            .where(Cart.session_id == session_id, Cart.is_active == True)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product),
                selectinload(Cart.items).selectinload(CartItem.variant)
            )
        )

    def get_or_create_user_cart(self, user_id: int) -> Cart:
        """Récupérer ou créer le panier d'un utilisateur"""
        cart = self.get_user_cart(user_id)
        
        if not cart:
            cart = Cart(
                user_id=user_id,
                currency="XOF",  # TODO: récupérer depuis les settings
                is_active=True
            )
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        
        return cart

    def get_or_create_session_cart(self, session_id: str) -> Cart:
        """Récupérer ou créer un panier de session"""
        cart = self.get_cart_by_session_id(session_id)
        
        if not cart:
            cart = Cart(
                session_id=session_id,
                currency="XOF",
                is_active=True
            )
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
        
        return cart

    def add_item_to_cart(self, cart_id: int, product_id: int, quantity: int = 1, 
                        variant_id: Optional[int] = None) -> Optional[CartItem]:
        """Ajouter un article au panier"""
        cart = self.get_cart_by_id(cart_id)
        if not cart:
            return None
        
        # Vérifier que le produit existe
        product = self.db.get(Product, product_id)
        if not product or not product.is_active:
            return None
        
        # Vérifier la variante si spécifiée
        variant = None
        if variant_id:
            variant = self.db.get(ProductVariant, variant_id)
            if not variant or not variant.is_active or variant.product_id != product_id:
                return None
        
        # Chercher si l'article existe déjà dans le panier
        existing_item = self.db.scalar(
            select(CartItem)
            .where(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id,
                CartItem.variant_id == variant_id
            )
        )
        
        if existing_item:
            # Augmenter la quantité
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.utcnow()
            # Mettre à jour le prix si nécessaire
            existing_item.update_price()
            item = existing_item
        else:
            # Créer un nouvel article
            item = CartItem(
                cart_id=cart_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity
            )
            # Définir le prix actuel
            item.update_price()
            self.db.add(item)
        
        # Mettre à jour le timestamp du panier
        cart.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_cart_item_quantity(self, cart_id: int, item_id: int, quantity: int) -> bool:
        """Mettre à jour la quantité d'un article du panier"""
        item = self.db.scalar(
            select(CartItem)
            .where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        )
        
        if not item:
            return False
        
        if quantity <= 0:
            # Supprimer l'article si quantité <= 0
            self.db.delete(item)
        else:
            item.quantity = quantity
            item.updated_at = datetime.utcnow()
            # Mettre à jour le prix
            item.update_price()
        
        # Mettre à jour le timestamp du panier
        cart = self.get_cart_by_id(cart_id)
        if cart:
            cart.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True

    def remove_cart_item(self, cart_id: int, item_id: int) -> bool:
        """Supprimer un article du panier"""
        item = self.db.scalar(
            select(CartItem)
            .where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        )
        
        if item:
            self.db.delete(item)
            
            # Mettre à jour le timestamp du panier
            cart = self.get_cart_by_id(cart_id)
            if cart:
                cart.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
        
        return False

    def clear_cart(self, cart_id: int) -> bool:
        """Vider complètement un panier"""
        cart = self.get_cart_by_id(cart_id)
        if not cart:
            return False
        
        # Supprimer tous les articles
        for item in cart.items:
            self.db.delete(item)
        
        cart.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def validate_cart(self, cart_id: int) -> List[str]:
        """Valider le contenu d'un panier"""
        cart = self.get_cart_by_id(cart_id)
        if not cart:
            return ["Panier non trouvé"]
        
        return cart.validate_items(self.db)

    def merge_carts(self, source_cart_id: int, target_cart_id: int) -> bool:
        """Fusionner deux paniers (utile lors de la connexion d'un utilisateur)"""
        source_cart = self.get_cart_by_id(source_cart_id)
        target_cart = self.get_cart_by_id(target_cart_id)
        
        if not source_cart or not target_cart:
            return False
        
        # Déplacer les articles du panier source vers le panier cible
        for item in source_cart.items:
            # Vérifier si l'article existe déjà dans le panier cible
            existing_item = self.db.scalar(
                select(CartItem)
                .where(
                    CartItem.cart_id == target_cart_id,
                    CartItem.product_id == item.product_id,
                    CartItem.variant_id == item.variant_id
                )
            )
            
            if existing_item:
                # Fusionner les quantités
                existing_item.quantity += item.quantity
                existing_item.updated_at = datetime.utcnow()
                self.db.delete(item)
            else:
                # Déplacer l'article
                item.cart_id = target_cart_id
                item.updated_at = datetime.utcnow()
        
        # Désactiver le panier source
        source_cart.is_active = False
        target_cart.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True

    def assign_cart_to_user(self, cart_id: int, user_id: int) -> bool:
        """Assigner un panier de session à un utilisateur connecté"""
        cart = self.get_cart_by_id(cart_id)
        if not cart or cart.user_id:
            return False
        
        # Vérifier s'il existe déjà un panier pour cet utilisateur
        existing_user_cart = self.get_user_cart(user_id)
        
        if existing_user_cart:
            # Fusionner les paniers
            self.merge_carts(cart_id, existing_user_cart.id)
        else:
            # Assigner simplement le panier à l'utilisateur
            cart.user_id = user_id
            cart.session_id = None
            cart.updated_at = datetime.utcnow()
            self.db.commit()
        
        return True

    def get_abandoned_carts(self, hours_ago: int = 24) -> List[Cart]:
        """Récupérer les paniers abandonnés"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
        
        return list(self.db.scalars(
            select(Cart)
            .where(
                Cart.is_active == True,
                Cart.updated_at < cutoff_time,
                func.array_length(Cart.items, 1) > 0  # Panier non vide
            )
            .options(
                selectinload(Cart.items),
                selectinload(Cart.user)
            )
        ))

    def cleanup_empty_carts(self, days_ago: int = 7) -> int:
        """Nettoyer les paniers vides anciens"""
        cutoff_time = datetime.utcnow() - timedelta(days=days_ago)
        
        # Récupérer les paniers vides anciens
        empty_carts = self.db.scalars(
            select(Cart)
            .where(
                Cart.updated_at < cutoff_time,
                ~Cart.items.any()  # Pas d'articles
            )
        ).all()
        
        count = len(empty_carts)
        
        # Supprimer les paniers vides
        for cart in empty_carts:
            self.db.delete(cart)
        
        self.db.commit()
        return count

    def get_cart_stats(self) -> dict:
        """Récupérer les statistiques des paniers"""
        total_carts = self.db.scalar(select(func.count(Cart.id)).where(Cart.is_active == True))
        
        carts_with_items = self.db.scalar(
            select(func.count(Cart.id))
            .where(Cart.is_active == True, Cart.items.any())
        )
        
        total_items = self.db.scalar(
            select(func.sum(CartItem.quantity))
            .select_from(Cart)
            .join(CartItem)
            .where(Cart.is_active == True)
        )
        
        return {
            "total_active_carts": total_carts or 0,
            "carts_with_items": carts_with_items or 0,
            "total_items_in_carts": total_items or 0,
            "average_items_per_cart": (total_items / carts_with_items) if carts_with_items else 0
        }
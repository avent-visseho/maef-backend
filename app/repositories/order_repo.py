# ===================================
# app/repositories/order_repo.py
# ===================================
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, timedelta

from app.models.order import Order, OrderItem, Shipment, OrderStatus, PaymentStatus
from app.models.user import User
from app.models.product import Product, ProductVariant


class OrderRepository:
    """Repository pour la gestion des commandes"""
    
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, user_id: Optional[int] = None, guest_email: Optional[str] = None, 
                     **kwargs) -> Order:
        """Créer une nouvelle commande"""
        order_number = Order.generate_order_number(self.db)
        
        order = Order(
            order_number=order_number,
            user_id=user_id,
            guest_email=guest_email,
            **kwargs
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_order_by_id(self, order_id: int, with_items: bool = True) -> Optional[Order]:
        """Récupérer une commande par son ID"""
        query = select(Order).where(Order.id == order_id)
        
        if with_items:
            query = query.options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.variant),
                selectinload(Order.user),
                selectinload(Order.payments),
                selectinload(Order.shipments)
            )
        
        return self.db.scalar(query)

    def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Récupérer une commande par son numéro"""
        return self.db.scalar(
            select(Order)
            .where(Order.order_number == order_number)
            .options(
                selectinload(Order.items),
                selectinload(Order.user),
                selectinload(Order.payments)
            )
        )

    def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 20, 
                       status: Optional[OrderStatus] = None) -> Tuple[List[Order], int]:
        """Récupérer les commandes d'un utilisateur"""
        query = select(Order).where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        
        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query)
        
        # Récupérer les commandes avec pagination
        orders = self.db.scalars(
            query.options(selectinload(Order.items))
            .order_by(desc(Order.created_at))
            .offset(skip)
            .limit(limit)
        ).all()
        
        return list(orders), total or 0

    def get_orders(self, skip: int = 0, limit: int = 50, 
                   status: Optional[OrderStatus] = None,
                   payment_status: Optional[PaymentStatus] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   search: Optional[str] = None) -> Tuple[List[Order], int]:
        """Récupérer toutes les commandes avec filtres (admin)"""
        query = select(Order)
        
        # Filtres
        conditions = []
        
        if status:
            conditions.append(Order.status == status)
        
        if payment_status:
            conditions.append(Order.payment_status == payment_status)
        
        if start_date:
            conditions.append(Order.created_at >= start_date)
        
        if end_date:
            conditions.append(Order.created_at <= end_date)
        
        if search:
            conditions.append(
                or_(
                    Order.order_number.ilike(f"%{search}%"),
                    Order.guest_email.ilike(f"%{search}%"),
                    Order.user.has(User.email.ilike(f"%{search}%"))
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query)
        
        # Récupérer avec pagination
        orders = self.db.scalars(
            query.options(
                joinedload(Order.user),
                selectinload(Order.items)
            )
            .order_by(desc(Order.created_at))
            .offset(skip)
            .limit(limit)
        ).all()
        
        return list(orders), total or 0

    def update_order_status(self, order_id: int, new_status: OrderStatus, 
                           notes: Optional[str] = None) -> Optional[Order]:
        """Mettre à jour le statut d'une commande"""
        order = self.get_order_by_id(order_id, with_items=False)
        if order:
            order.update_status(new_status, notes)
            self.db.commit()
            self.db.refresh(order)
        return order

    def add_order_item(self, order_id: int, product_id: int, quantity: int, 
                       variant_id: Optional[int] = None) -> Optional[OrderItem]:
        """Ajouter un article à une commande"""
        order = self.get_order_by_id(order_id, with_items=False)
        if not order:
            return None
        
        # Récupérer le produit et le prix
        product = self.db.get(Product, product_id)
        if not product:
            return None
        
        variant = self.db.get(ProductVariant, variant_id) if variant_id else None
        
        # Déterminer le prix
        unit_price = product.current_price or 0
        if variant and variant.price_adjustment:
            unit_price += variant.price_adjustment
        
        # Créer l'item
        item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            currency=order.currency,
            product_title=product.title,
            product_sku=variant.sku if variant else product.sku_root,
            variant_name=variant.name if variant else None
        )
        
        self.db.add(item)
        
        # Recalculer les totaux
        order.calculate_totals()
        
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_order_item(self, order_id: int, item_id: int) -> bool:
        """Supprimer un article d'une commande"""
        item = self.db.scalar(
            select(OrderItem)
            .where(OrderItem.id == item_id, OrderItem.order_id == order_id)
        )
        
        if item:
            order = item.order
            self.db.delete(item)
            order.calculate_totals()
            self.db.commit()
            return True
        
        return False

    def create_shipment(self, order_id: int, **kwargs) -> Optional[Shipment]:
        """Créer une expédition pour une commande"""
        order = self.get_order_by_id(order_id, with_items=False)
        if not order:
            return None
        
        shipment = Shipment(order_id=order_id, **kwargs)
        self.db.add(shipment)
        self.db.commit()
        self.db.refresh(shipment)
        return shipment

    def get_order_stats(self, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None) -> dict:
        """Récupérer les statistiques des commandes"""
        query = select(Order)
        
        if start_date:
            query = query.where(Order.created_at >= start_date)
        if end_date:
            query = query.where(Order.created_at <= end_date)
        
        orders = self.db.scalars(query).all()
        
        stats = {
            "total_orders": len(orders),
            "total_revenue": sum(float(o.grand_total) for o in orders if o.is_paid),
            "average_order_value": 0,
            "orders_by_status": {},
            "orders_by_payment_status": {}
        }
        
        if stats["total_orders"] > 0:
            stats["average_order_value"] = stats["total_revenue"] / stats["total_orders"]
        
        # Grouper par statut
        for order in orders:
            status = order.status.value
            stats["orders_by_status"][status] = stats["orders_by_status"].get(status, 0) + 1
            
            payment_status = order.payment_status.value
            stats["orders_by_payment_status"][payment_status] = stats["orders_by_payment_status"].get(payment_status, 0) + 1
        
        return stats

    def get_recent_orders(self, limit: int = 10) -> List[Order]:
        """Récupérer les commandes récentes"""
        return list(self.db.scalars(
            select(Order)
            .options(joinedload(Order.user))
            .order_by(desc(Order.created_at))
            .limit(limit)
        ))

    def get_pending_orders(self) -> List[Order]:
        """Récupérer les commandes en attente de traitement"""
        return list(self.db.scalars(
            select(Order)
            .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]))
            .options(selectinload(Order.items))
            .order_by(Order.created_at)
        ))

    def cancel_order(self, order_id: int, reason: Optional[str] = None) -> Optional[Order]:
        """Annuler une commande"""
        order = self.get_order_by_id(order_id, with_items=False)
        
        if order and order.can_be_cancelled:
            order.update_status(OrderStatus.CANCELLED, reason)
            
            # TODO: Libérer les réservations de stock
            # TODO: Annuler/rembourser les paiements si nécessaire
            
            self.db.commit()
            self.db.refresh(order)
            
        return order

    def delete_order(self, order_id: int) -> bool:
        """Supprimer définitivement une commande (admin uniquement)"""
        order = self.get_order_by_id(order_id, with_items=False)
        
        if order and order.status in [OrderStatus.CANCELLED, OrderStatus.PENDING]:
            self.db.delete(order)
            self.db.commit()
            return True
        
        return False

    def get_orders_requiring_attention(self) -> List[Order]:
        """Récupérer les commandes nécessitant une attention (retards, problèmes)"""
        # Commandes payées mais non expédiées depuis plus de 2 jours
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        
        return list(self.db.scalars(
            select(Order)
            .where(
                and_(
                    Order.payment_status == PaymentStatus.PAID,
                    Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PROCESSING]),
                    Order.confirmed_at < two_days_ago
                )
            )
            .options(joinedload(Order.user))
            .order_by(Order.confirmed_at)
        ))
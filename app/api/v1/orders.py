# ===================================
# app/api/v1/orders.py
# ===================================
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, require_scope
from app.api.deps import get_pagination_params
from app.repositories.order_repo import OrderRepository
from app.models.user import User
from app.schemas.order import OrdersListResponse, OrderResponse

router = APIRouter()

@router.get("/", response_model=OrdersListResponse)
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Récupérer les commandes de l'utilisateur connecté"""
    order_repo = OrderRepository(db)
    
    orders, total = order_repo.get_user_orders(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return OrdersListResponse(
        data=[order.to_dict() for order in orders],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        has_more=(skip + limit) < total
    )

@router.get("/admin", response_model=OrdersListResponse)
def list_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_scope("orders:read")),
    db: Session = Depends(get_db)
) -> Any:
    """Récupérer toutes les commandes (Admin)"""
    order_repo = OrderRepository(db)
    
    orders, total = order_repo.get_orders(
        skip=skip,
        limit=limit
    )
    
    return OrdersListResponse(
        data=[order.to_dict() for order in orders],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        has_more=(skip + limit) < total
    )

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Récupérer une commande par ID"""
    order_repo = OrderRepository(db)
    order = order_repo.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande non trouvée"
        )
    
    # Vérifier que l'utilisateur peut accéder à cette commande
    if order.user_id != current_user.id and not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé à cette commande"
        )
    
    return OrderResponse(
        message="Commande récupérée avec succès",
        data=order.to_dict()
    )
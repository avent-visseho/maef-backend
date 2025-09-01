# ===================================
# app/api/v1/cart.py
# ===================================
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.api.deps import get_current_user_or_none
from app.repositories.cart_repo import CartRepository
from app.repositories.product_repo import get_product_by_id
from app.schemas.cart import (
    Cart,
    CartItem,
    CartItemCreate,
    CartItemUpdate,
    CartResponse,
    CartValidationResponse
)
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=CartResponse)
def get_cart(
    session_id: Optional[str] = Query(None, description="ID de session pour les utilisateurs non connectés"),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer le panier de l'utilisateur connecté ou par session
    """
    cart_repo = CartRepository(db)
    
    if current_user:
        # Utilisateur connecté - récupérer ou créer son panier
        cart = cart_repo.get_or_create_user_cart(current_user.id)
    elif session_id:
        # Utilisateur non connecté avec session ID
        cart = cart_repo.get_cart_by_session_id(session_id)
        if not cart:
            cart = cart_repo.get_or_create_session_cart(session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requis pour les utilisateurs non connectés"
        )
    
    return CartResponse(
        message="Panier récupéré avec succès",
        data=Cart.from_orm(cart)
    )


@router.post("/items", response_model=CartResponse)
def add_item_to_cart(
    item_data: CartItemCreate,
    session_id: Optional[str] = Query(None, description="ID de session pour les utilisateurs non connectés"),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
) -> Any:
    """
    Ajouter un article au panier
    """
    cart_repo = CartRepository(db)
    
    # Vérifier que le produit existe
    product = get_product_by_id(db, item_data.product_id)
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé ou inactif"
        )
    
    # Récupérer ou créer le panier
    if current_user:
        cart = cart_repo.get_or_create_user_cart(current_user.id)
    elif session_id:
        cart = cart_repo.get_or_create_session_cart(session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requis pour les utilisateurs non connectés"
        )
    
    # Ajouter l'article
    cart_item = cart_repo.add_item_to_cart(
        cart_id=cart.id,
        product_id=item_data.product_id,
        quantity=item_data.quantity,
        variant_id=item_data.variant_id
    )
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'ajouter l'article au panier"
        )
    
    # Récupérer le panier mis à jour
    updated_cart = cart_repo.get_cart_by_id(cart.id)
    
    return CartResponse(
        message="Article ajouté au panier avec succès",
        data=Cart.from_orm(updated_cart)
    )


@router.put("/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    session_id: Optional[str] = Query(None, description="ID de session pour les utilisateurs non connectés"),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
) -> Any:
    """
    Mettre à jour la quantité d'un article du panier
    """
    cart_repo = CartRepository(db)
    
    # Récupérer le panier
    if current_user:
        cart = cart_repo.get_user_cart(current_user.id)
    elif session_id:
        cart = cart_repo.get_cart_by_session_id(session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requis pour les utilisateurs non connectés"
        )
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Panier non trouvé"
        )
    
    # Mettre à jour l'article
    success = cart_repo.update_cart_item_quantity(
        cart_id=cart.id,
        item_id=item_id,
        quantity=item_update.quantity
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article non trouvé dans le panier"
        )
    
    # Récupérer le panier mis à jour
    updated_cart = cart_repo.get_cart_by_id(cart.id)
    
    return CartResponse(
        message="Article mis à jour avec succès",
        data=Cart.from_orm(updated_cart)
    )


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    item_id: int,
    session_id: Optional[str] = Query(None, description="ID de session pour les utilisateurs non connectés"),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
) -> Any:
    """
    Supprimer un article du panier
    """
    cart_repo = CartRepository(db)
    
    # Récupérer le panier
    if current_user:
        cart = cart_repo.get_user_cart(current_user.id)
    elif session_id:
        cart = cart_repo.get_cart_by_session_id(session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requis pour les utilisateurs non connectés"
        )
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Panier non trouvé"
        )
    
    # Supprimer l'article
    success = cart_repo.remove_cart_item(cart_id=cart.id, item_id=item_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article non trouvé dans le panier"
        )
    
    # Récupérer le panier mis à jour
    updated_cart = cart_repo.get_cart_by_id(cart.id)
    
    return CartResponse(
        message="Article supprimé avec succès",
        data=Cart.from_orm(updated_cart)
    )


@router.delete("/", response_model=dict)
def clear_cart(
    session_id: Optional[str] = Query(None, description="ID de session pour les utilisateurs non connectés"),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
) -> Any:
    """
    Vider complètement le panier
    """
    cart_repo = CartRepository(db)
    
    # Récupérer le panier
    if current_user:
        cart = cart_repo.get_user_cart(current_user.id)
    elif session_id:
        cart = cart_repo.get_cart_by_session_id(session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requis pour les utilisateurs non connectés"
        )
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Panier non trouvé"
        )
    
    # Vider le panier
    success = cart_repo.clear_cart(cart_id=cart.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de vider le panier"
        )
    
    return {
        "success": True,
        "message": "Panier vidé avec succès"
    }


@router.post("/validate", response_model=CartValidationResponse)
def validate_cart(
    session_id: Optional[str] = Query(None, description="ID de session pour les utilisateurs non connectés"),
    current_user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db)
) -> Any:
    """
    Valider le contenu du panier (stock, prix, disponibilité)
    """
    cart_repo = CartRepository(db)
    
    # Récupérer le panier
    if current_user:
        cart = cart_repo.get_user_cart(current_user.id)
    elif session_id:
        cart = cart_repo.get_cart_by_session_id(session_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID requis pour les utilisateurs non connectés"
        )
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Panier non trouvé"
        )
    
    # Valider les articles
    validation_errors = cart_repo.validate_cart(cart_id=cart.id)
    
    # Récupérer le panier mis à jour (au cas où des articles auraient été supprimés)
    updated_cart = cart_repo.get_cart_by_id(cart.id)
    
    return CartValidationResponse(
        message="Validation du panier terminée",
        data=Cart.from_orm(updated_cart),
        is_valid=len(validation_errors) == 0,
        errors=validation_errors
    )


@router.post("/merge", response_model=CartResponse)
def merge_carts(
    guest_session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Fusionner un panier de session avec le panier utilisateur (lors de la connexion)
    """
    cart_repo = CartRepository(db)
    
    # Récupérer le panier de session
    guest_cart = cart_repo.get_cart_by_session_id(guest_session_id)
    if not guest_cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Panier de session non trouvé"
        )
    
    # Récupérer ou créer le panier utilisateur
    user_cart = cart_repo.get_or_create_user_cart(current_user.id)
    
    # Fusionner les paniers
    success = cart_repo.merge_carts(
        source_cart_id=guest_cart.id,
        target_cart_id=user_cart.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de fusionner les paniers"
        )
    
    # Récupérer le panier fusionné
    merged_cart = cart_repo.get_cart_by_id(user_cart.id)
    
    return CartResponse(
        message="Paniers fusionnés avec succès",
        data=Cart.from_orm(merged_cart)
    )


@router.get("/stats", response_model=dict)
def get_cart_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer les statistiques des paniers (admin seulement)
    """
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis"
        )
    
    cart_repo = CartRepository(db)
    stats = cart_repo.get_cart_stats()
    
    return {
        "success": True,
        "message": "Statistiques des paniers récupérées",
        "data": stats
    }
# ===================================
# app/api/v1/reviews.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.get("/product/{product_id}")
def get_product_reviews(product_id: int):
    """Récupérer les avis d'un produit"""
    return {"message": f"Avis produit {product_id} - À implémenter"}

@router.post("/")
def create_review(current_user: User = Depends(get_current_active_user)):
    """Créer un nouvel avis"""
    return {"message": "Créer avis - À implémenter"}
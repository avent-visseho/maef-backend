# ===================================
# app/api/v1/promotions.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_scope

router = APIRouter()

@router.get("/")
def list_promotions():
    """Récupérer toutes les promotions actives"""
    return {"message": "Liste promotions - À implémenter"}

@router.post("/")
def create_promotion(current_user = Depends(require_scope("admin"))):
    """Créer une nouvelle promotion"""
    return {"message": "Créer promotion - À implémenter"}

@router.post("/validate-coupon")
def validate_coupon():
    """Valider un code promo"""
    return {"message": "Validation coupon - À implémenter"}
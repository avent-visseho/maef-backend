# ===================================
# app/api/v1/inventory.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_scope

router = APIRouter()

@router.get("/")
def get_inventory_overview(current_user = Depends(require_scope("admin"))):
    """Vue d'ensemble de l'inventaire"""
    return {"message": "Inventaire overview - À implémenter"}

@router.post("/adjust-stock")
def adjust_stock(current_user = Depends(require_scope("admin"))):
    """Ajuster le stock d'un produit"""
    return {"message": "Ajustement stock - À implémenter"}

@router.get("/low-stock")
def get_low_stock_products(current_user = Depends(require_scope("admin"))):
    """Produits en stock faible"""
    return {"message": "Stock faible - À implémenter"}
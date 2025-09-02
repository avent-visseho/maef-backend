# ===================================
# app/api/v1/search.py
# ===================================
from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/")
def search_products(q: str = Query(..., description="Terme de recherche")):
    """Recherche de produits"""
    return {"message": f"Recherche pour: {q} - À implémenter"}
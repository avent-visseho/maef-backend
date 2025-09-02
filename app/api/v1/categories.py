# ===================================
# app/api/v1/categories.py
# ===================================
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.category import Category

router = APIRouter()

@router.get("/")
def list_categories():
    """Récupérer toutes les catégories"""
    return {"message": "Liste des catégories - À implémenter"}

@router.get("/{category_id}")
def get_category():
    """Récupérer une catégorie par ID"""
    return {"message": "Catégorie par ID - À implémenter"}

@router.post("/")
def create_category():
    """Créer une nouvelle catégorie"""
    return {"message": "Créer catégorie - À implémenter"}


# app/api/v1/media.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    """Upload d'un fichier média"""
    return {"message": "Upload média - À implémenter"}

@router.get("/{asset_id}")
async def get_media(asset_id: int):
    """Récupérer un média par ID"""
    return {"message": "Récupération média - À implémenter"}

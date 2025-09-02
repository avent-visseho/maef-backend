# ===================================
# app/api/v1/checkout.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/")
def create_checkout_session(current_user: User = Depends(get_current_active_user)):
    """Créer une session de checkout"""
    return {"message": "Checkout - À implémenter"}

@router.get("/{session_id}")
def get_checkout_session(session_id: str):
    """Récupérer une session de checkout"""
    return {"message": "Session checkout - À implémenter"}
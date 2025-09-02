# ===================================
# app/api/v1/payments.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/stripe/create-intent")
def create_payment_intent(current_user: User = Depends(get_current_active_user)):
    """Créer un intent de paiement Stripe"""
    return {"message": "Paiement Stripe - À implémenter"}

@router.post("/fedapay/create-transaction")
def create_fedapay_transaction(current_user: User = Depends(get_current_active_user)):
    """Créer une transaction FedaPay"""
    return {"message": "Paiement FedaPay - À implémenter"}
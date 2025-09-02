# ===================================
# app/api/v1/webhooks.py
# ===================================
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """Webhook Stripe pour les événements de paiement"""
    return {"message": "Webhook Stripe - À implémenter"}

@router.post("/fedapay")
async def fedapay_webhook(request: Request):
    """Webhook FedaPay pour les événements de paiement"""
    return {"message": "Webhook FedaPay - À implémenter"}

@router.post("/instagram")
async def instagram_webhook(request: Request):
    """Webhook Instagram pour les nouvelles stories"""
    return {"message": "Webhook Instagram - À implémenter"}
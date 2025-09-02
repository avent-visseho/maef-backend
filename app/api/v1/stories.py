# ===================================
# app/api/v1/stories.py
# ===================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_scope

router = APIRouter()

@router.get("/")
def list_stories():
    """Récupérer toutes les stories"""
    return {"message": "Liste stories - À implémenter"}

@router.post("/ingest/instagram")
def ingest_instagram_stories(current_user = Depends(require_scope("stories:write"))):
    """Ingérer les stories depuis Instagram"""
    return {"message": "Ingestion Instagram - À implémenter"}

@router.get("/{story_id}")
def get_story(story_id: int):
    """Récupérer une story par ID"""
    return {"message": f"Story {story_id} - À implémenter"}
# ===================================
# Fichier: app/models/review.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Review(Base):
    __tablename__ = "review"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Note (1-5 étoiles)
    rating = Column(Integer, nullable=False)
    
    # Avis
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    
    # Modération
    is_approved = Column(Boolean, default=False)
    is_verified_purchase = Column(Boolean, default=False)  # Achat vérifié
    
    # Réponse du vendeur
    seller_response = Column(Text, nullable=True)
    seller_response_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

    def __repr__(self):
        return f"<Review(id={self.id}, product_id={self.product_id}, rating={self.rating})>"
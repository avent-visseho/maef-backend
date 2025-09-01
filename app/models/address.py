# ===================================
# app/models/address.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AddressType(str, enum.Enum):
    BILLING = "billing"
    SHIPPING = "shipping"
    BOTH = "both"


class Address(Base):
    __tablename__ = "address"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Type d'adresse
    kind = Column(Enum(AddressType), nullable=False, default=AddressType.BOTH)
    
    # Informations personnelles
    full_name = Column(String, nullable=False)
    company = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    # Adresse
    line1 = Column(String, nullable=False)  # Adresse principale
    line2 = Column(String, nullable=True)   # Complément d'adresse
    city = Column(String, nullable=False)
    state = Column(String, nullable=True)   # État/Province
    country = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    
    # Options
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    user = relationship("User", back_populates="addresses")

    def __repr__(self):
        return f"<Address(id={self.id}, user_id={self.user_id}, city='{self.city}')>"

    @property
    def full_address(self):
        """Adresse complète formatée"""
        address_parts = [self.line1]
        if self.line2:
            address_parts.append(self.line2)
        address_parts.extend([self.city, self.zip_code, self.country])
        return ", ".join(address_parts)

    def to_dict(self):
        """Convertir en dictionnaire pour l'API"""
        return {
            "id": self.id,
            "kind": self.kind,
            "full_name": self.full_name,
            "company": self.company,
            "phone": self.phone,
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "zip_code": self.zip_code,
            "is_default": self.is_default,
            "full_address": self.full_address
        }
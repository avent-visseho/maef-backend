# ===================================
# app/models/category.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from typing import List, Optional

from app.core.database import Base


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey('category.id', ondelete='CASCADE'), nullable=True)
    
    # Informations principales
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Hiérarchie et affichage
    position = Column(Integer, default=0)  # Ordre d'affichage
    level = Column(Integer, default=0)     # Niveau dans la hiérarchie (0=racine)
    
    # SEO
    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    
    # État
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Image de la catégorie
    image_url = Column(String, nullable=True)
    
    # Statistiques
    products_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    products = relationship("Product", secondary="product_category", back_populates="categories")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', level={self.level})>"

    @hybrid_property
    def full_name(self):
        """Nom complet avec hiérarchie (ex: "Vêtements > Femme > Robes")"""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name

    @hybrid_property
    def is_root(self):
        """Vérifier si c'est une catégorie racine"""
        return self.parent_id is None

    @hybrid_property
    def has_children(self):
        """Vérifier si la catégorie a des sous-catégories"""
        return len(self.children) > 0

    def get_all_children(self, include_self: bool = False) -> List['Category']:
        """Récupérer toutes les sous-catégories (récursif)"""
        result = [self] if include_self else []
        for child in self.children:
            result.extend(child.get_all_children(include_self=True))
        return result

    def get_ancestors(self, include_self: bool = False) -> List['Category']:
        """Récupérer toutes les catégories parentes"""
        result = [self] if include_self else []
        if self.parent:
            result = self.parent.get_ancestors(include_self=True) + result
        return result

    def get_breadcrumb(self) -> List[dict]:
        """Récupérer le fil d'Ariane"""
        ancestors = self.get_ancestors(include_self=True)
        return [{"id": cat.id, "name": cat.name, "slug": cat.slug} for cat in ancestors]

    def get_root_category(self) -> 'Category':
        """Récupérer la catégorie racine"""
        if self.is_root:
            return self
        return self.parent.get_root_category()

    def update_products_count(self, db_session):
        """Mettre à jour le compteur de produits"""
        from app.models.product import product_category_table
        from sqlalchemy import select, func as sql_func
        
        # Compter les produits directement dans cette catégorie
        count = db_session.scalar(
            select(sql_func.count()).select_from(product_category_table).where(
                product_category_table.c.category_id == self.id
            )
        )
        
        self.products_count = count or 0
        db_session.commit()

    def update_hierarchy_level(self, db_session):
        """Mettre à jour le niveau hiérarchique"""
        if self.parent_id:
            if self.parent:
                self.level = self.parent.level + 1
            else:
                # Récupérer le parent depuis la DB
                parent = db_session.get(Category, self.parent_id)
                self.level = parent.level + 1 if parent else 0
        else:
            self.level = 0
        
        # Mettre à jour les enfants récursivement
        for child in self.children:
            child.level = self.level + 1
            child.update_hierarchy_level(db_session)

    def can_be_parent_of(self, potential_child: 'Category') -> bool:
        """Vérifier si cette catégorie peut être parent d'une autre (éviter les cycles)"""
        # Une catégorie ne peut pas être son propre parent
        if self.id == potential_child.id:
            return False
        
        # Une catégorie ne peut pas avoir comme parent une de ses sous-catégories
        child_ids = [child.id for child in self.get_all_children()]
        if potential_child.id in child_ids:
            return False
        
        return True

    @classmethod
    def get_featured(cls, db_session) -> List['Category']:
        """Récupérer les catégories mises en avant"""
        from sqlalchemy import select
        return db_session.execute(
            select(cls).where(cls.is_featured == True, cls.is_active == True)
            .order_by(cls.position, cls.name)
        ).scalars().all()

    @classmethod
    def get_roots(cls, db_session) -> List['Category']:
        """Récupérer toutes les catégories racines"""
        from sqlalchemy import select
        return db_session.execute(
            select(cls).where(cls.parent_id == None, cls.is_active == True)
            .order_by(cls.position, cls.name)
        ).scalars().all()

    @classmethod
    def build_tree(cls, categories: List['Category']) -> List[dict]:
        """Construire l'arbre hiérarchique à partir d'une liste de catégories"""
        category_dict = {cat.id: {
            "category": cat,
            "children": []
        } for cat in categories}
        
        tree = []
        
        for cat in categories:
            cat_data = category_dict[cat.id]
            if cat.parent_id and cat.parent_id in category_dict:
                category_dict[cat.parent_id]["children"].append(cat_data)
            else:
                tree.append(cat_data)
        
        return tree
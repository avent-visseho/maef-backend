from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func, and_, or_, desc, asc, text
from datetime import datetime

from app.models.product import Product, ProductVariant, Price, Tag, ProductMedia
from app.models.category import Category
from app.models.inventory import Inventory


class ProductRepository:
    """Repository pour la gestion des produits"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_product_by_id(self, product_id: int, with_variants: bool = True, 
                         with_media: bool = True) -> Optional[Product]:
        """Récupérer un produit par son ID"""
        query = select(Product).where(Product.id == product_id)
        
        options = []
        if with_variants:
            options.append(selectinload(Product.variants))
        if with_media:
            options.append(selectinload(Product.media).selectinload(ProductMedia.asset))
        
        options.extend([
            selectinload(Product.categories),
            selectinload(Product.tags),
            selectinload(Product.prices),
            selectinload(Product.inventory)
        ])
        
        return self.db.scalar(query.options(*options))

    def get_product_by_slug(self, slug: str) -> Optional[Product]:
        """Récupérer un produit par son slug"""
        return self.db.scalar(
            select(Product)
            .where(Product.slug == slug)
            .options(
                selectinload(Product.variants),
                selectinload(Product.media).selectinload(ProductMedia.asset),
                selectinload(Product.categories),
                selectinload(Product.tags),
                selectinload(Product.prices),
                selectinload(Product.inventory)
            )
        )

    def get_product_by_sku(self, sku: str) -> Optional[Product]:
        """Récupérer un produit par son SKU"""
        return self.db.scalar(select(Product).where(Product.sku_root == sku))

    def get_products(self, skip: int = 0, limit: int = 20,
                    search: Optional[str] = None,
                    category_id: Optional[int] = None,
                    brand: Optional[str] = None,
                    min_price: Optional[float] = None,
                    max_price: Optional[float] = None,
                    is_featured: Optional[bool] = None,
                    is_active: Optional[bool] = True,
                    sort_by: str = "created_at",
                    sort_order: str = "desc") -> Tuple[List[Product], int]:
        """Récupérer les produits avec filtres et pagination"""
        
        query = select(Product)
        
        # Filtres
        conditions = []
        
        if is_active is not None:
            conditions.append(Product.is_active == is_active)
        
        if is_featured is not None:
            conditions.append(Product.is_featured == is_featured)
        
        if brand:
            conditions.append(Product.brand.ilike(f"%{brand}%"))
        
        if category_id:
            conditions.append(Product.categories.any(Category.id == category_id))
        
        if search:
            # Recherche dans le titre, description et marque
            search_condition = or_(
                Product.title.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%")
            )
            conditions.append(search_condition)
        
        # Filtres de prix (nécessite une jointure avec Price)
        if min_price is not None or max_price is not None:
            query = query.join(Price, and_(
                Price.product_id == Product.id,
                Price.is_active == True,
                Price.starts_at <= datetime.utcnow(),
                or_(Price.ends_at.is_(None), Price.ends_at >= datetime.utcnow())
            ))
            
            if min_price is not None:
                conditions.append(Price.amount >= min_price)
            if max_price is not None:
                conditions.append(Price.amount <= max_price)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query)
        
        # Tri
        order_column = getattr(Product, sort_by, Product.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Pagination et options
        products = self.db.scalars(
            query.options(
                selectinload(Product.media).selectinload(ProductMedia.asset),
                selectinload(Product.prices),
                selectinload(Product.inventory)
            )
            .offset(skip)
            .limit(limit)
        ).all()
        
        return list(products), total or 0

    def create_product(self, product_data: dict) -> Product:
        """Créer un nouveau produit"""
        product = Product(**product_data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(self, product_id: int, update_data: dict) -> Optional[Product]:
        """Mettre à jour un produit"""
        product = self.get_product_by_id(product_id, with_variants=False, with_media=False)
        if not product:
            return None
        
        for field, value in update_data.items():
            if hasattr(product, field) and value is not None:
                setattr(product, field, value)
        
        product.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(product)
        return product

    def soft_delete_product(self, product_id: int) -> bool:
        """Désactiver un produit (soft delete)"""
        product = self.get_product_by_id(product_id, with_variants=False, with_media=False)
        if product:
            product.is_active = False
            product.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def create_variant(self, variant_data: dict) -> ProductVariant:
        """Créer une variante de produit"""
        variant = ProductVariant(**variant_data)
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def update_variant(self, variant_id: int, update_data: dict) -> Optional[ProductVariant]:
        """Mettre à jour une variante"""
        variant = self.db.get(ProductVariant, variant_id)
        if not variant:
            return None
        
        for field, value in update_data.items():
            if hasattr(variant, field) and value is not None:
                setattr(variant, field, value)
        
        variant.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def delete_variant(self, variant_id: int) -> bool:
        """Supprimer une variante"""
        variant = self.db.get(ProductVariant, variant_id)
        if variant:
            self.db.delete(variant)
            self.db.commit()
            return True
        return False

    def add_media_to_product(self, product_id: int, asset_id: int, 
                           is_primary: bool = False, position: int = 0,
                           alt_text: Optional[str] = None) -> ProductMedia:
        """Ajouter un média à un produit"""
        # Si c'est marqué comme principal, retirer le principal actuel
        if is_primary:
            self.db.execute(
                select(ProductMedia)
                .where(ProductMedia.product_id == product_id)
                .values(is_primary=False)
            )
        
        media = ProductMedia(
            product_id=product_id,
            asset_id=asset_id,
            is_primary=is_primary,
            position=position,
            alt_text=alt_text
        )
        
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        return media

    def remove_media_from_product(self, product_id: int, media_id: int) -> bool:
        """Supprimer un média d'un produit"""
        media = self.db.scalar(
            select(ProductMedia)
            .where(ProductMedia.id == media_id, ProductMedia.product_id == product_id)
        )
        
        if media:
            self.db.delete(media)
            self.db.commit()
            return True
        return False

    def increment_views(self, product_id: int) -> bool:
        """Incrémenter le compteur de vues"""
        product = self.db.get(Product, product_id)
        if product:
            product.views_count += 1
            self.db.commit()
            return True
        return False

    def get_featured_products(self, limit: int = 10) -> List[Product]:
        """Récupérer les produits mis en avant"""
        return list(self.db.scalars(
            select(Product)
            .where(Product.is_featured == True, Product.is_active == True)
            .options(
                selectinload(Product.media).selectinload(ProductMedia.asset),
                selectinload(Product.prices)
            )
            .order_by(desc(Product.sales_count))
            .limit(limit)
        ))

    def search_products_fulltext(self, query: str, limit: int = 20) -> List[Product]:
        """Recherche full-text dans les produits (PostgreSQL FTS)"""
        # TODO: Implémenter la recherche FTS PostgreSQL
        # Pour l'instant, utiliser une recherche LIKE simple
        return list(self.db.scalars(
            select(Product)
            .where(
                and_(
                    Product.is_active == True,
                    or_(
                        Product.title.ilike(f"%{query}%"),
                        Product.description.ilike(f"%{query}%"),
                        Product.brand.ilike(f"%{query}%")
                    )
                )
            )
            .options(
                selectinload(Product.media).selectinload(ProductMedia.asset),
                selectinload(Product.prices)
            )
            .limit(limit)
        ))
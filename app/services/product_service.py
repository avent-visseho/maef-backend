# ===================================
# app/services/product_service.py
# ===================================

from typing import List, Optional
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.product import Product, ProductVariant, Price
from app.models.inventory import Inventory
from app.models.category import Category
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate, ProductVariantCreate


class ProductService:
    """Service pour la logique métier des produits"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(db)

    def create_product(self, product_data: ProductCreate, created_by: int) -> Product:
        """Créer un produit complet avec prix et stock"""
        # Générer le slug si non fourni
        slug = product_data.slug
        if not slug:
            slug = self._generate_slug(product_data.title)
        
        # Créer le produit
        product_dict = product_data.dict(exclude={
            'category_ids', 'tag_ids', 'media_ids', 'price', 
            'compare_at_price', 'initial_stock'
        })
        product_dict['slug'] = slug
        
        product = self.product_repo.create_product(product_dict)
        
        # Ajouter le prix initial
        self._create_initial_price(product, product_data.price, product_data.compare_at_price)
        
        # Ajouter le stock initial
        self._create_initial_inventory(product, product_data.initial_stock)
        
        # Associer les catégories
        if product_data.category_ids:
            self._associate_categories(product, product_data.category_ids)
        
        # Associer les médias
        if product_data.media_ids:
            self._associate_media(product, product_data.media_ids)
        
        return product

    def update_product(self, product_id: int, product_update: ProductUpdate, 
                      updated_by: int) -> Optional[Product]:
        """Mettre à jour un produit"""
        update_data = product_update.dict(exclude_unset=True)
        return self.product_repo.update_product(product_id, update_data)

    def create_variant(self, product_id: int, variant_data: ProductVariantCreate,
                      created_by: int) -> Optional[ProductVariant]:
        """Créer une variante de produit"""
        variant_dict = variant_data.dict()
        variant_dict['product_id'] = product_id
        
        variant = self.product_repo.create_variant(variant_dict)
        
        # Créer l'inventaire pour la variante
        if variant_data.initial_stock > 0:
            inventory = Inventory(
                variant_id=variant.id,
                qty_on_hand=variant_data.initial_stock,
                location="main"
            )
            self.db.add(inventory)
            self.db.commit()
        
        return variant

    def get_related_products(self, product_id: int, limit: int = 4) -> List[Product]:
        """Récupérer les produits connexes basés sur les catégories"""
        product = self.product_repo.get_product_by_id(product_id, with_variants=False)
        if not product or not product.categories:
            return []
        
        # Récupérer les produits des mêmes catégories
        category_ids = [cat.id for cat in product.categories]
        
        related_products, _ = self.product_repo.get_products(
            limit=limit * 2,  # Récupérer plus pour filtrer
            category_id=category_ids[0],  # Prendre la première catégorie
            is_active=True
        )
        
        # Filtrer le produit actuel et limiter
        filtered = [p for p in related_products if p.id != product_id][:limit]
        
        return filtered

    def increment_views(self, product_id: int) -> bool:
        """Incrémenter les vues d'un produit"""
        return self.product_repo.increment_views(product_id)

    def add_media_to_product(self, product_id: int, media_data, created_by: int):
        """Ajouter un média à un produit"""
        return self.product_repo.add_media_to_product(
            product_id=product_id,
            asset_id=media_data.asset_id,
            is_primary=media_data.is_primary,
            position=media_data.position,
            alt_text=media_data.alt_text
        )

    def _generate_slug(self, title: str) -> str:
        """Générer un slug unique à partir du titre"""
        import re
        base_slug = re.sub(r'[^\w\s-]', '', title.lower())
        base_slug = re.sub(r'[-\s]+', '-', base_slug).strip('-')
        
        # Vérifier l'unicité
        counter = 1
        slug = base_slug
        
        while self.product_repo.get_product_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug

    def _create_initial_price(self, product: Product, amount: Decimal, 
                            compare_at_amount: Optional[Decimal] = None):
        """Créer le prix initial du produit"""
        price = Price(
            product_id=product.id,
            amount=amount,
            compare_at_amount=compare_at_amount,
            currency="XOF",
            is_active=True
        )
        self.db.add(price)
        self.db.commit()

    def _create_initial_inventory(self, product: Product, initial_stock: int):
        """Créer l'inventaire initial du produit"""
        if initial_stock > 0:
            inventory = Inventory(
                product_id=product.id,
                qty_on_hand=initial_stock,
                location="main"
            )
            self.db.add(inventory)
            self.db.commit()

    def _associate_categories(self, product: Product, category_ids: List[int]):
        """Associer des catégories au produit"""
        categories = self.db.query(Category).filter(Category.id.in_(category_ids)).all()
        product.categories.extend(categories)
        self.db.commit()

    def _associate_media(self, product: Product, media_ids: List[int]):
        """Associer des médias au produit"""
        for i, media_id in enumerate(media_ids):
            self.product_repo.add_media_to_product(
                product_id=product.id,
                asset_id=media_id,
                is_primary=(i == 0),  # Premier média = principal
                position=i
            )
# ===================================
# app/api/v1/products.py
# ===================================
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, require_scope, require_roles
from app.api.deps import get_pagination_params
from app.repositories.product_repo import ProductRepository
from app.services.product_service import ProductService
from app.schemas.product import (
    Product,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductsListResponse,
    ProductDetail,
    ProductVariant,
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductMedia,
    ProductMediaCreate
)
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=ProductsListResponse)
def list_products(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments à retourner"),
    search: Optional[str] = Query(None, description="Terme de recherche"),
    category_id: Optional[int] = Query(None, description="Filtrer par catégorie"),
    brand: Optional[str] = Query(None, description="Filtrer par marque"),
    min_price: Optional[float] = Query(None, ge=0, description="Prix minimum"),
    max_price: Optional[float] = Query(None, ge=0, description="Prix maximum"),
    is_featured: Optional[bool] = Query(None, description="Produits mis en avant"),
    is_active: Optional[bool] = Query(True, description="Produits actifs seulement"),
    sort_by: Optional[str] = Query("created_at", description="Tri par: created_at, title, price, sales_count"),
    sort_order: Optional[str] = Query("desc", description="Ordre: asc, desc"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer la liste des produits avec filtres et pagination
    """
    product_repo = ProductRepository(db)
    
    products, total = product_repo.get_products(
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        is_featured=is_featured,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return ProductsListResponse(
        data=[Product.from_orm(product) for product in products],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        has_more=(skip + limit) < total
    )


@router.get("/featured", response_model=ProductsListResponse)
def get_featured_products(
    limit: int = Query(10, ge=1, le=50, description="Nombre de produits à retourner"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer les produits mis en avant
    """
    product_repo = ProductRepository(db)
    
    products, total = product_repo.get_products(
        skip=0,
        limit=limit,
        is_featured=True,
        is_active=True,
        sort_by="sales_count",
        sort_order="desc"
    )
    
    return ProductsListResponse(
        data=[Product.from_orm(product) for product in products],
        total=total,
        page=1,
        per_page=limit,
        has_more=False
    )


@router.get("/best-sellers", response_model=ProductsListResponse)
def get_best_sellers(
    limit: int = Query(10, ge=1, le=50, description="Nombre de produits à retourner"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer les meilleures ventes
    """
    product_repo = ProductRepository(db)
    
    products, total = product_repo.get_products(
        skip=0,
        limit=limit,
        is_active=True,
        sort_by="sales_count",
        sort_order="desc"
    )
    
    return ProductsListResponse(
        data=[Product.from_orm(product) for product in products],
        total=total,
        page=1,
        per_page=limit,
        has_more=False
    )


@router.get("/{product_slug}", response_model=ProductResponse)
def get_product(
    product_slug: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer un produit par son slug avec toutes ses informations
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    product = product_repo.get_product_by_slug(product_slug)
    
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Incrémenter le compteur de vues
    product_service.increment_views(product.id)
    
    return ProductResponse(
        message="Produit récupéré avec succès",
        data=ProductDetail.from_orm(product)
    )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(require_scope("products:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Créer un nouveau produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    # Vérifier que le SKU n'existe pas déjà
    if product_repo.get_product_by_sku(product_data.sku_root):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un produit avec ce SKU existe déjà"
        )
    
    # Créer le produit
    product = product_service.create_product(product_data, current_user.id)
    
    return ProductResponse(
        message="Produit créé avec succès",
        data=ProductDetail.from_orm(product)
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(require_scope("products:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Mettre à jour un produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Mettre à jour le produit
    updated_product = product_service.update_product(product_id, product_update, current_user.id)
    
    return ProductResponse(
        message="Produit mis à jour avec succès",
        data=ProductDetail.from_orm(updated_product)
    )


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(require_scope("products:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Supprimer un produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Soft delete - désactiver le produit
    success = product_repo.soft_delete_product(product_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer le produit"
        )
    
    return {
        "success": True,
        "message": "Produit supprimé avec succès"
    }


# Gestion des variantes
@router.post("/{product_id}/variants", response_model=ProductResponse)
def create_product_variant(
    product_id: int,
    variant_data: ProductVariantCreate,
    current_user: User = Depends(require_scope("products:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Créer une variante de produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Créer la variante
    variant = product_service.create_variant(product_id, variant_data, current_user.id)
    
    # Récupérer le produit mis à jour
    updated_product = product_repo.get_product_by_id(product_id, with_variants=True)
    
    return ProductResponse(
        message="Variante créée avec succès",
        data=ProductDetail.from_orm(updated_product)
    )


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductResponse)
def update_product_variant(
    product_id: int,
    variant_id: int,
    variant_update: ProductVariantUpdate,
    current_user: User = Depends(require_scope("products:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Mettre à jour une variante de produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Mettre à jour la variante
    variant = product_service.update_variant(variant_id, variant_update, current_user.id)
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante non trouvée"
        )
    
    # Récupérer le produit mis à jour
    updated_product = product_repo.get_product_by_id(product_id, with_variants=True)
    
    return ProductResponse(
        message="Variante mise à jour avec succès",
        data=ProductDetail.from_orm(updated_product)
    )


@router.delete("/{product_id}/variants/{variant_id}")
def delete_product_variant(
    product_id: int,
    variant_id: int,
    current_user: User = Depends(require_scope("products:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Supprimer une variante de produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Supprimer la variante
    success = product_repo.delete_variant(variant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variante non trouvée"
        )
    
    return {
        "success": True,
        "message": "Variante supprimée avec succès"
    }


# Gestion des médias produit
@router.post("/{product_id}/media", response_model=ProductResponse)

def create_product_media(
    product_id: int,
    media_data: ProductMediaCreate,
    current_user: User = Depends(require_scope("media:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Ajouter un média à un produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Ajouter le média
    media = product_service.add_media_to_product(product_id, media_data, current_user.id)
    
    # Récupérer le produit mis à jour
    updated_product = product_repo.get_product_by_id(product_id, with_media=True)
    
    return ProductResponse(
        message="Média ajouté avec succès",
        data=ProductDetail.from_orm(updated_product)
    )


@router.delete("/{product_id}/media/{media_id}")
def remove_product_media(
    product_id: int,
    media_id: int,
    current_user: User = Depends(require_scope("media:write")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Supprimer un média d'un produit (Admin/Manager)
    """
    product_repo = ProductRepository(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    # Supprimer le média
    success = product_repo.remove_media_from_product(product_id, media_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Média non trouvé"
        )
    
    return {
        "success": True,
        "message": "Média supprimé avec succès"
    }


@router.get("/related/{product_id}", response_model=ProductsListResponse)
def get_related_products(
    product_id: int,
    limit: int = Query(4, ge=1, le=20, description="Nombre de produits connexes"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer les produits connexes
    """
    product_repo = ProductRepository(db)
    product_service = ProductService(db)
    
    product = product_repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit non trouvé"
        )
    
    related_products = product_service.get_related_products(product_id, limit)
    
    return ProductsListResponse(
        data=[Product.from_orm(p) for p in related_products],
        total=len(related_products),
        page=1,
        per_page=limit,
        has_more=False
    )
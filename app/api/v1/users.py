# ===================================
# app/api/v1/users.py
# ===================================
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user, require_scope, require_roles
from app.repositories.user_repo import (
    get_users,
    get_user_by_id,
    update_user,
    delete_user,
    get_all_roles,
    assign_role_to_user,
    remove_role_from_user,
    get_user_addresses,
    get_address_by_id
)
from app.schemas.user import (
    User,
    UserUpdate,
    UserResponse,
    UsersListResponse,
    UserRoleAssignment,
    Role,
    Address,
    AddressCreate,
    AddressUpdate
)
from app.models.address import Address as AddressModel

router = APIRouter()


@router.get("/", response_model=UsersListResponse)
def list_users(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments à retourner"),
    search: Optional[str] = Query(None, description="Terme de recherche"),
    is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    role_name: Optional[str] = Query(None, description="Filtrer par rôle"),
    current_user: User = Depends(require_scope("admin")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer la liste des utilisateurs (Admin seulement)
    """
    users, total = get_users(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
        role_name=role_name
    )
    
    return UsersListResponse(
        data=[User.from_orm(user) for user in users],
        total=total,
        page=(skip // limit) + 1,
        per_page=limit
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Récupérer le profil de l'utilisateur connecté
    """
    return UserResponse(
        message="Profil utilisateur récupéré avec succès",
        data=User.from_orm(current_user)
    )


@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Mettre à jour le profil de l'utilisateur connecté
    """
    # Ne pas permettre la modification du statut is_active
    if hasattr(user_update, 'is_active'):
        user_update.is_active = None
    
    updated_user = update_user(db=db, user_id=current_user.id, user_update=user_update)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return UserResponse(
        message="Profil mis à jour avec succès",
        data=User.from_orm(updated_user)
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(require_scope("admin")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer un utilisateur par son ID (Admin seulement)
    """
    user = get_user_by_id(db=db, user_id=user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return UserResponse(
        message="Utilisateur récupéré avec succès",
        data=User.from_orm(user)
    )


@router.put("/{user_id}", response_model=UserResponse)
def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_scope("admin")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Mettre à jour un utilisateur (Admin seulement)
    """
    updated_user = update_user(db=db, user_id=user_id, user_update=user_update)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return UserResponse(
        message="Utilisateur mis à jour avec succès",
        data=User.from_orm(updated_user)
    )


@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_scope("admin")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Désactiver un utilisateur (Admin seulement)
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de se désactiver soi-même"
        )
    
    success = delete_user(db=db, user_id=user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return {
        "success": True,
        "message": "Utilisateur désactivé avec succès"
    }


@router.get("/roles/all", response_model=List[Role])
def list_all_roles(
    current_user: User = Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer tous les rôles disponibles
    """
    roles = get_all_roles(db=db)
    return [Role.from_orm(role) for role in roles]


@router.post("/{user_id}/roles", response_model=UserResponse)
def assign_roles_to_user(
    user_id: int,
    role_assignment: UserRoleAssignment,
    current_user: User = Depends(require_scope("admin")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Assigner des rôles à un utilisateur (Admin seulement)
    """
    user = get_user_by_id(db=db, user_id=user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Assigner les nouveaux rôles
    for role_id in role_assignment.role_ids:
        success = assign_role_to_user(db=db, user_id=user_id, role_id=role_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible d'assigner le rôle ID {role_id}"
            )
    
    # Récupérer l'utilisateur mis à jour
    updated_user = get_user_by_id(db=db, user_id=user_id)
    
    return UserResponse(
        message="Rôles assignés avec succès",
        data=User.from_orm(updated_user)
    )


@router.delete("/{user_id}/roles/{role_id}")
def remove_role_from_user_endpoint(
    user_id: int,
    role_id: int,
    current_user: User = Depends(require_scope("admin")),
    db: Session = Depends(get_db)
) -> Any:
    """
    Retirer un rôle d'un utilisateur (Admin seulement)
    """
    success = remove_role_from_user(db=db, user_id=user_id, role_id=role_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de retirer le rôle"
        )
    
    return {
        "success": True,
        "message": "Rôle retiré avec succès"
    }


# Gestion des adresses utilisateur
@router.get("/me/addresses", response_model=List[Address])
def get_my_addresses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Récupérer les adresses de l'utilisateur connecté
    """
    addresses = get_user_addresses(db=db, user_id=current_user.id)
    return [Address.from_orm(addr) for addr in addresses]


@router.post("/me/addresses", response_model=Address, status_code=status.HTTP_201_CREATED)
def create_address(
    address_data: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Créer une nouvelle adresse pour l'utilisateur connecté
    """
    # Si c'est marqué comme adresse par défaut, retirer le défaut des autres
    if address_data.is_default:
        db.query(AddressModel).filter(
            AddressModel.user_id == current_user.id
        ).update({"is_default": False})
    
    new_address = AddressModel(
        user_id=current_user.id,
        **address_data.dict()
    )
    
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    
    return Address.from_orm(new_address)


@router.put("/me/addresses/{address_id}", response_model=Address)
def update_my_address(
    address_id: int,
    address_update: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Mettre à jour une adresse de l'utilisateur connecté
    """
    address = get_address_by_id(db=db, address_id=address_id, user_id=current_user.id)
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adresse non trouvée"
        )
    
    update_data = address_update.dict(exclude_unset=True)
    
    # Si c'est marqué comme adresse par défaut, retirer le défaut des autres
    if update_data.get("is_default"):
        db.query(AddressModel).filter(
            AddressModel.user_id == current_user.id,
            AddressModel.id != address_id
        ).update({"is_default": False})
    
    for field, value in update_data.items():
        setattr(address, field, value)
    
    db.commit()
    db.refresh(address)
    
    return Address.from_orm(address)


@router.delete("/me/addresses/{address_id}")
def delete_my_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Supprimer une adresse de l'utilisateur connecté
    """
    address = get_address_by_id(db=db, address_id=address_id, user_id=current_user.id)
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adresse non trouvée"
        )
    
    address.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": "Adresse supprimée avec succès"
    }
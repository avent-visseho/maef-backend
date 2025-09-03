# ===================================
# app/api/v1/media.py
# ===================================
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status
from fastapi.responses import FileResponse
from typing import List, Optional
import os
import shutil
import uuid
from pathlib import Path
import mimetypes
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_active_user
from app.schemas.user import User
from app.core.database import get_db

router = APIRouter()

# Créer le répertoire de médias s'il n'existe pas
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

# Sous-répertoires pour différents types de médias
IMAGES_DIR = MEDIA_DIR / "images"
VIDEOS_DIR = MEDIA_DIR / "videos"
DOCUMENTS_DIR = MEDIA_DIR / "documents"

for dir_path in [IMAGES_DIR, VIDEOS_DIR, DOCUMENTS_DIR]:
    dir_path.mkdir(exist_ok=True)


def validate_file_type(file: UploadFile, allowed_types: List[str]) -> bool:
    """Valider le type de fichier"""
    if file.content_type not in allowed_types:
        return False
    return True


def validate_file_size(file: UploadFile, max_size: int) -> bool:
    """Valider la taille du fichier"""
    # Note: Cette validation est approximative car file.size peut être None
    # Pour une validation précise, il faudrait lire le fichier
    if hasattr(file, 'size') and file.size and file.size > max_size:
        return False
    return True


def generate_unique_filename(original_filename: str) -> str:
    """Générer un nom de fichier unique"""
    file_extension = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{file_extension}"
    return unique_name


@router.post("/upload/image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload d'une image"""
    
    # Validation du type de fichier
    if not validate_file_type(file, settings.ALLOWED_IMAGE_TYPES):
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé. Types acceptés: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # Validation de la taille
    if not validate_file_size(file, settings.MAX_FILE_SIZE):
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Taille maximale: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    try:
        # Générer un nom de fichier unique
        unique_filename = generate_unique_filename(file.filename)
        file_path = IMAGES_DIR / unique_filename
        
        # Sauvegarder le fichier
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Retourner les informations du fichier
        return {
            "success": True,
            "data": {
                "filename": unique_filename,
                "original_name": file.filename,
                "file_path": str(file_path),
                "url": f"/api/v1/media/images/{unique_filename}",
                "content_type": file.content_type,
                "size": file_path.stat().st_size
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload: {str(e)}"
        )


@router.post("/upload/video", status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload d'une vidéo"""
    
    # Validation du type de fichier
    if not validate_file_type(file, settings.ALLOWED_VIDEO_TYPES):
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé. Types acceptés: {', '.join(settings.ALLOWED_VIDEO_TYPES)}"
        )
    
    # Validation de la taille
    if not validate_file_size(file, settings.MAX_FILE_SIZE):
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux. Taille maximale: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    try:
        # Générer un nom de fichier unique
        unique_filename = generate_unique_filename(file.filename)
        file_path = VIDEOS_DIR / unique_filename
        
        # Sauvegarder le fichier
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Retourner les informations du fichier
        return {
            "success": True,
            "data": {
                "filename": unique_filename,
                "original_name": file.filename,
                "file_path": str(file_path),
                "url": f"/api/v1/media/videos/{unique_filename}",
                "content_type": file.content_type,
                "size": file_path.stat().st_size
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload: {str(e)}"
        )


@router.post("/upload/multiple", status_code=status.HTTP_201_CREATED)
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload de plusieurs fichiers"""
    
    if len(files) > 10:  # Limiter le nombre de fichiers
        raise HTTPException(
            status_code=400,
            detail="Nombre maximum de fichiers dépassé (10 max)"
        )
    
    uploaded_files = []
    
    for file in files:
        try:
            # Déterminer le type et le répertoire de destination
            if file.content_type in settings.ALLOWED_IMAGE_TYPES:
                target_dir = IMAGES_DIR
                url_prefix = "images"
            elif file.content_type in settings.ALLOWED_VIDEO_TYPES:
                target_dir = VIDEOS_DIR
                url_prefix = "videos"
            else:
                continue  # Ignorer les fichiers non supportés
            
            # Validation de la taille
            if not validate_file_size(file, settings.MAX_FILE_SIZE):
                continue  # Ignorer les fichiers trop volumineux
            
            # Générer un nom de fichier unique
            unique_filename = generate_unique_filename(file.filename)
            file_path = target_dir / unique_filename
            
            # Sauvegarder le fichier
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "filename": unique_filename,
                "original_name": file.filename,
                "file_path": str(file_path),
                "url": f"/api/v1/media/{url_prefix}/{unique_filename}",
                "content_type": file.content_type,
                "size": file_path.stat().st_size
            })
            
        except Exception as e:
            # Continuer avec les autres fichiers en cas d'erreur
            continue
    
    return {
        "success": True,
        "data": {
            "uploaded_count": len(uploaded_files),
            "total_files": len(files),
            "files": uploaded_files
        }
    }


@router.get("/images/{filename}")
async def get_image(filename: str):
    """Récupérer une image"""
    file_path = IMAGES_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Image non trouvée"
        )
    
    # Déterminer le type MIME
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        content_type = "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=filename
    )


@router.get("/videos/{filename}")
async def get_video(filename: str):
    """Récupérer une vidéo"""
    file_path = VIDEOS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Vidéo non trouvée"
        )
    
    # Déterminer le type MIME
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        content_type = "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=filename
    )


@router.delete("/images/{filename}")
async def delete_image(
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """Supprimer une image"""
    file_path = IMAGES_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Image non trouvée"
        )
    
    try:
        file_path.unlink()  # Supprimer le fichier
        return {
            "success": True,
            "message": "Image supprimée avec succès"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


@router.delete("/videos/{filename}")
async def delete_video(
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """Supprimer une vidéo"""
    file_path = VIDEOS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Vidéo non trouvée"
        )
    
    try:
        file_path.unlink()  # Supprimer le fichier
        return {
            "success": True,
            "message": "Vidéo supprimée avec succès"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


@router.get("/list")
async def list_media_files(
    media_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Lister les fichiers médias"""
    
    files_info = []
    
    # Fonction pour traiter un répertoire
    def process_directory(directory: Path, url_prefix: str, file_type: str):
        if directory.exists():
            for file_path in directory.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files_info.append({
                        "filename": file_path.name,
                        "type": file_type,
                        "url": f"/api/v1/media/{url_prefix}/{file_path.name}",
                        "size": stat.st_size,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime
                    })
    
    # Traiter selon le type demandé
    if media_type is None or media_type == "images":
        process_directory(IMAGES_DIR, "images", "image")
    
    if media_type is None or media_type == "videos":
        process_directory(VIDEOS_DIR, "videos", "video")
    
    # Trier par date de modification (plus récent en premier)
    files_info.sort(key=lambda x: x["modified_at"], reverse=True)
    
    return {
        "success": True,
        "data": {
            "files": files_info,
            "count": len(files_info)
        }
    }


@router.get("/info/{media_type}/{filename}")
async def get_media_info(
    media_type: str,
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """Obtenir les informations d'un fichier média"""
    
    if media_type == "images":
        file_path = IMAGES_DIR / filename
    elif media_type == "videos":
        file_path = VIDEOS_DIR / filename
    else:
        raise HTTPException(
            status_code=400,
            detail="Type de média non supporté"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Fichier non trouvé"
        )
    
    stat = file_path.stat()
    content_type, _ = mimetypes.guess_type(str(file_path))
    
    return {
        "success": True,
        "data": {
            "filename": filename,
            "type": media_type,
            "url": f"/api/v1/media/{media_type}/{filename}",
            "content_type": content_type,
            "size": stat.st_size,
            "size_human": f"{stat.st_size / (1024*1024):.2f} MB" if stat.st_size > 1024*1024 else f"{stat.st_size / 1024:.2f} KB",
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime
        }
    }
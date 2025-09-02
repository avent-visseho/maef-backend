"""
Models package initialization.
This file imports all models to make them available to Alembic for autogeneration.
"""

# IMPORTANT: Utiliser la MÊME Base que celle de database.py
from app.core.database import Base

# Import all your models here so they are registered with Base.metadata
# This is crucial for Alembic autogeneration to work

try:
    from .user import *  # User, Role, Permission
except ImportError:
    pass

try:
    from .product import *  # Product, Variant, SKU, Price, Media, Tag
except ImportError:
    pass

try:
    from .category import *
except ImportError:
    pass

try:
    from .story import *  # Story, StoryProductLink, OAuthToken
except ImportError:
    pass

try:
    from .inventory import *  # Stock, Reservation
except ImportError:
    pass

try:
    from .order import *  # Order, OrderItem, Shipment
except ImportError:
    pass

try:
    from .cart import *  # Cart, CartItem
except ImportError:
    pass

try:
    from .promotion import *  # Promotion, Coupon
except ImportError:
    pass

try:
    from .review import *
except ImportError:
    pass

try:
    from .payment import *  # Payment, Refund
except ImportError:
    pass

try:
    from .address import *  # Address (shipping/billing)
except ImportError:
    pass

try:
    from .media import *  # MediaAsset (bytea/LO), Derivative
except ImportError:
    pass

try:
    from .job import *  # JobQueue, JobAttempt (background léger)
except ImportError:
    pass

# Export Base so it can be imported from app.models
__all__ = ['Base']
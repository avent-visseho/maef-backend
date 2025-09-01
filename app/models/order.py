# ===================================
# app/models/order.py
# ===================================
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import List, Optional

from app.core.
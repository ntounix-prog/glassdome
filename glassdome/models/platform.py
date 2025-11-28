"""
Platform module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
from sqlalchemy import Column, String, JSON, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from glassdome.core.database import Base
from enum import Enum
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class PlatformType(str, Enum):
    """Platform type enumeration"""
    PROXMOX = "proxmox"
    AZURE = "azure"
    AWS = "aws"


class Platform(Base):
    """Platform configuration for deployment targets"""
    __tablename__ = "platforms"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Platform details
    name = Column(String(255), nullable=False)
    platform_type = Column(SQLEnum(PlatformType), nullable=False)
    
    # Connection details (encrypted)
    credentials = Column(JSON, nullable=False)
    
    # Platform capabilities
    capabilities = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Health check
    last_health_check = Column(DateTime(timezone=True))
    health_status = Column(String(50))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


"""
Lab module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from glassdome.core.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Lab(Base):
    """Lab configuration - represents a cyber range environment"""
    __tablename__ = "labs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Lab definition (drag-and-drop canvas data)
    canvas_data = Column(JSON, nullable=True)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    elements = relationship("LabElement", back_populates="lab", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="lab")


class LabTemplate(Base):
    """Reusable lab templates"""
    __tablename__ = "lab_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "Red Team", "Web Security", "Network"
    
    # Template definition
    template_data = Column(JSON, nullable=False)
    
    # Metadata
    is_public = Column(Boolean, default=False)
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Usage stats
    usage_count = Column(Integer, default=0)


class LabElement(Base):
    """Individual elements in a lab (VMs, networks, etc.)"""
    __tablename__ = "lab_elements"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=False)
    
    # Element type: vm, network, service, etc.
    element_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Configuration specific to element type
    config = Column(JSON, nullable=False)
    
    # Position on canvas
    position_x = Column(Integer)
    position_y = Column(Integer)
    
    # Dependencies (other elements this depends on)
    dependencies = Column(JSON, default=list)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    lab = relationship("Lab", back_populates="elements")


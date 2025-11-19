"""
Deployment Tracking Models
"""
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base
from enum import Enum
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class DeploymentStatus(str, Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"


class Deployment(Base):
    """Deployment instance - tracks actual deployed labs"""
    __tablename__ = "deployments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=False)
    
    # Deployment details
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)
    
    # Platform where deployed
    platform_id = Column(String, ForeignKey("platforms.id"))
    
    # Deployment configuration
    deployment_config = Column(JSON)
    
    # Deployed resources (IDs, IPs, etc.)
    resources = Column(JSON, default=dict)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(255))
    
    # Error information
    error_message = Column(Text)
    error_trace = Column(Text)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Cost tracking (for cloud deployments)
    estimated_cost_per_hour = Column(Integer)  # In cents
    
    # Auto-shutdown
    auto_shutdown_at = Column(DateTime(timezone=True))
    
    # Relationships
    lab = relationship("Lab", back_populates="deployments")
    platform = relationship("Platform")


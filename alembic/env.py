"""
Alembic Migration Environment

This configures Alembic to work with Glassdome's async SQLAlchemy setup.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import create_engine

from alembic import context

# Import our models and base
from glassdome.core.database import Base
from glassdome.core.config import settings

# Import all models to ensure they're registered with Base.metadata
# Reaper models
from glassdome.reaper.exploit_library import Exploit, ExploitMission, MissionLog, ValidationResult
from glassdome.reaper.hot_spare import HotSpare

# Networking models
from glassdome.networking.models import (
    NetworkDefinition, PlatformNetworkMapping, VMInterface, DeployedVM
)

# Whitepawn models
from glassdome.whitepawn.models import (
    WhitePawnDeployment, NetworkAlert, MonitoringEvent, ConnectivityMatrix
)

# Original models (if they exist)
try:
    from glassdome.models.deployment import Deployment
    from glassdome.models.lab import Lab, LabTemplate, LabElement
    from glassdome.models.platform import Platform
except ImportError:
    pass  # Optional models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Get database URL from settings (convert async to sync for Alembic)
def get_url():
    """Get database URL, converting async driver to sync for migrations."""
    url = settings.database_url
    # Alembic needs sync driver
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using sync engine."""
    url = get_url()
    
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

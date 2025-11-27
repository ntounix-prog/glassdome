"""
Database Configuration and Session Management
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from glassdome.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    # Import models to register them with Base
    from glassdome.reaper.exploit_library import Exploit, ExploitMission, MissionLog, ValidationResult
    from glassdome.reaper.hot_spare import HotSpare
    from glassdome.networking.models import NetworkDefinition, PlatformNetworkMapping, VMInterface, DeployedVM
    from glassdome.whitepawn.models import WhitePawnDeployment, NetworkAlert, MonitoringEvent, ConnectivityMatrix
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


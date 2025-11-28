# database/connection.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base
from config import DATABASE_URL
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db(reset: bool = False):
    try:
        async with engine.begin() as conn:
            if reset:
                logger.warning("⚠️ Dropping all tables and resetting database...")
                await conn.run_sync(Base.metadata.drop_all)
            
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
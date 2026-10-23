import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

def normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL URLs for asyncpg:
    - Converts postgres:// or postgresql:// to postgresql+asyncpg://
    - Removes libpq-specific query params like 'channel_binding', 'sslmode'
    - Ensures 'ssl=require' is present for remote SSL connections
    """
    parts = urlsplit(url)
    scheme = parts.scheme

    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    query_params = dict(parse_qsl(parts.query))
    clean_params = {}

    # Neon and most cloud Postgres require SSL
    if "sslmode" in query_params or "ssl" in query_params or "neon.tech" in parts.netloc:
        clean_params["ssl"] = "require"

    # Forward other asyncpg-compatible options if any
    for k in ("server_settings", "statement_cache_size", "command_timeout"):
        if k in query_params:
            clean_params[k] = query_params[k]

    new_parts = parts._replace(scheme=scheme, query=urlencode(clean_params))
    return urlunsplit(new_parts)

CLEAN_DATABASE_URL = normalize_database_url(DATABASE_URL)

engine = create_async_engine(
    CLEAN_DATABASE_URL,
    echo=False,
    future=True,
    # Neon serverless: pool settings
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

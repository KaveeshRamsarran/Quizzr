"""
Database Configuration
SQLAlchemy async engine and session management
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from uuid import uuid4

from sqlalchemy import MetaData, event, inspect, text
from sqlalchemy.engine import make_url

from app.config import settings


# Naming conventions for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = metadata


# Convert sync database URL to async
def get_async_database_url(url: str) -> str:
    """Convert postgresql:// to postgresql+asyncpg:// or handle sqlite"""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def postgres_engine_options(url: str) -> tuple[str, dict]:
    """Return (url, engine kwargs) for a PostgreSQL URL.

    Handles the libpq-style options hosted databases such as Supabase put in their
    connection strings (asyncpg does not understand ``sslmode``), and the Supabase
    transaction pooler (port 6543), which cannot keep prepared statements.
    """
    parsed = make_url(url)
    query = dict(parsed.query)
    connect_args: dict = {}

    sslmode = query.pop("sslmode", None)
    host = parsed.host or ""
    is_supabase = host.endswith(".supabase.co") or host.endswith(".supabase.com")
    if sslmode in {"require", "verify-ca", "verify-full"} or (is_supabase and sslmode != "disable"):
        connect_args["ssl"] = "require"
    elif sslmode == "disable":
        connect_args["ssl"] = False

    if parsed.port == 6543 or query.pop("pgbouncer", None) == "true":
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"

    # Hosted plans cap connections (Supabase Nano: 60 in total), so keep the pool small there.
    pool_size, max_overflow = (5, 5) if is_supabase else (10, 20)
    options = {
        "pool_pre_ping": True,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "connect_args": connect_args,
    }
    return parsed.set(query=query).render_as_string(hide_password=False), options


# Check if using SQLite
_async_url = get_async_database_url(settings.database_url)
is_sqlite = _async_url.startswith("sqlite")

# Create async engine with appropriate settings
if is_sqlite:
    engine = create_async_engine(
        _async_url,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    _pg_url, _pg_options = postgres_engine_options(_async_url)
    engine = create_async_engine(_pg_url, echo=False, **_pg_options)


# Columns added after the first release. create_all() only creates missing tables,
# so existing databases get these with ALTER TABLE on startup.
_ADDED_COLUMNS = {
    "users": {"supabase_id": "VARCHAR(64)"},
}


def upgrade_schema(sync_conn) -> None:
    """Bring an existing database up to date with the models (run inside run_sync)."""
    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in tables:
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in existing:
                sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
    if "users" in tables:
        user_indexes = {ix["name"] for ix in inspect(sync_conn).get_indexes("users")}
        if "ix_users_supabase_id" not in user_indexes:
            sync_conn.execute(text("CREATE UNIQUE INDEX ix_users_supabase_id ON users (supabase_id)"))

    if sync_conn.dialect.name == "postgresql":
        # Supabase publishes every table in the public schema through its Data API,
        # reachable with the anon key the browser holds. Row level security with no
        # policies closes that door; the API connects as the table owner, which RLS
        # does not apply to, so Quizzr itself is unaffected.
        for table in Base.metadata.sorted_tables:
            sync_conn.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for compatibility
get_session = get_db

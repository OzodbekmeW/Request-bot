"""
Alembic Environment Configuration
"""
from logging.config import fileConfig

from sqlalchemy import pool, engine_from_config
from sqlalchemy.engine import Connection

from alembic import context

# Import models and base
from app.core.database import Base
from app.core.config import settings
from app.models import (
    User, Admin, Permission, OTPCode, RefreshToken, AdminSession
)

# Alembic Config object
config = context.config

# Override sqlalchemy.url with sync URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync engine."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Alembic environment configuration for clean architecture migrations."""
import logging
from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import your models here to ensure they're available for autogenerate
from models import db

# Import the common database engine
from app.common.db import DATABASE_URL, engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the database URL from environment
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schema information for better migrations
        include_schemas=True,
        # Compare types for better detection
        compare_type=True,
        # Compare server defaults
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the engine from common.db if available, otherwise create from config
    connectable = engine

    if connectable is None:
        # fallback to creating engine from config
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include schema information for better migrations
            include_schemas=True,
            # Compare types for better detection
            compare_type=True,
            # Compare server defaults
            compare_server_default=True,
            # Ignore certain tables if needed
            # include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


def include_object(object, name: str, type_: str, reflected: bool, compare_to: Optional[object]) -> bool:
    """
    Filter function to determine which objects to include in migrations.

    This can be used to exclude certain tables or schemas from migrations.
    """
    # Example: exclude temporary tables
    if type_ == "table" and name.startswith("temp_"):
        return False

    # Example: exclude certain schemas
    if hasattr(object, "schema") and object.schema in ["information_schema", "pg_catalog"]:
        return False

    return True


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
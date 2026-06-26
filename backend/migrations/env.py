from __future__ import annotations

import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.config import Config
from app.db.base import db
from app.db import models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", Config.DATABASE_URL)
target_metadata = db.metadata
_POSTGRES_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _postgres_schema() -> str:
    schema = os.getenv("DATABASE_SCHEMA", "public").strip() or "public"
    if not _POSTGRES_SCHEMA_RE.match(schema):
        raise ValueError("DATABASE_SCHEMA must be a simple PostgreSQL schema name")
    return schema


def _configure_postgres_schema(connection) -> dict:
    if connection.dialect.name != "postgresql":
        return {}

    schema = _postgres_schema()
    connection.execute(text(f'SET search_path TO "{schema}"'))
    connection.commit()
    return {"version_table_schema": schema}


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **_configure_postgres_schema(connection),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

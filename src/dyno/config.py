"""Settings from the environment (or a local .env file). Secrets never live in code.

Per-suite choices (which agent, which scorers, how many repeats) belong in the suite's
YAML file, not here: this is only what differs between machines.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: a blank line such as "ANTHROPIC_API_KEY=" (as in .env.example)
    # means "not set", not an empty value.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    # Where runs, cases, results and steps are stored. SQLite by default (one file,
    # nothing to install); any SQLAlchemy URL works, e.g. Postgres.
    database_url: str = "sqlite:///dyno.db"
    # The judge scorers (from M4) call Claude through this key.
    anthropic_api_key: SecretStr | None = None
    log_level: str = "WARNING"


@lru_cache
def get_settings() -> Settings:
    return Settings()

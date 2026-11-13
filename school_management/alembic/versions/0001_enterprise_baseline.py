"""Enterprise Relational Baseline (SQLite + PostgreSQL)

Revision ID: 0001_enterprise_baseline
Revises:
Create Date: 2026-04-01 00:00:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_enterprise_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Ensure full commercial SQLAlchemy schema & non-destructive legacy upgrades.
    Creates missing tables (including Inventory & SchemaVersion) and safely
    migrates pre-existing SQLite rows without dropping data.
    """
    from app.database.migrations import migrate_database

    bind = op.get_bind()
    migrate_database(bind.engine)


def downgrade() -> None:
    """
    Non-destructive baseline: downgrade intentionally raises to protect school production data.
    """
    raise NotImplementedError(
        "Automatic downgrade of the commercial baseline schema is blocked to prevent data loss."
    )

"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "businesses",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("google_place_id", sa.Text(), nullable=True),
        sa.Column("yelp_id", sa.Text(), nullable=True),
        sa.Column("existing_website", sa.Text(), nullable=True),
        sa.Column("website_score", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'discovered'"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_place_id", name="uq_businesses_google_place_id"),
        sa.UniqueConstraint("yelp_id", name="uq_businesses_yelp_id"),
        sa.UniqueConstraint("name", "city", "state", name="uq_businesses_name_city_state"),
    )

    op.create_table(
        "business_assets",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column(
            "photos",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hours", sa.JSON(), nullable=True),
        sa.Column("rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("review_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("reviews_summary", sa.Text(), nullable=True),
        sa.Column(
            "social_links",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=True,
        ),
        sa.Column(
            "services",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=True,
        ),
        sa.Column("price_range", sa.Text(), nullable=True),
        sa.Column(
            "raw_google",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=True,
        ),
        sa.Column(
            "raw_yelp",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_business_assets_business_id"),
    )

    op.create_table(
        "sites",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("template_used", sa.Text(), nullable=False),
        sa.Column("vercel_url", sa.Text(), nullable=True),
        sa.Column("custom_subdomain", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("deployed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_sites_business_id"),
    )

    op.create_table(
        "outreach",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=True),
        sa.Column("email_to", sa.Text(), nullable=True),
        sa.Column("email_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("email_status", sa.Text(), nullable=True),
        sa.Column("form_submitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("form_status", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "jobs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("last_run_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("outreach")
    op.drop_table("sites")
    op.drop_table("business_assets")
    op.drop_table("businesses")

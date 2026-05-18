"""initial schema

Revision ID: 202605180001
Revises:
Create Date: 2026-05-18 00:01:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605180001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bid_raw_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("crawl_status", sa.String(length=32), server_default="saved", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index(op.f("ix_bid_raw_documents_content_hash"), "bid_raw_documents", ["content_hash"], unique=False)
    op.create_index(op.f("ix_bid_raw_documents_crawl_status"), "bid_raw_documents", ["crawl_status"], unique=False)
    op.create_index(op.f("ix_bid_raw_documents_id"), "bid_raw_documents", ["id"], unique=False)
    op.create_index(op.f("ix_bid_raw_documents_publish_date"), "bid_raw_documents", ["publish_date"], unique=False)
    op.create_index(op.f("ix_bid_raw_documents_region"), "bid_raw_documents", ["region"], unique=False)
    op.create_index(op.f("ix_bid_raw_documents_source_name"), "bid_raw_documents", ["source_name"], unique=False)
    op.create_index(op.f("ix_bid_raw_documents_title"), "bid_raw_documents", ["title"], unique=False)

    op.create_table(
        "crawl_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=64), server_default="mock_public_bid", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("rate_limit_seconds", sa.Integer(), server_default="3", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_crawl_sources_name"),
    )
    op.create_index(op.f("ix_crawl_sources_id"), "crawl_sources", ["id"], unique=False)
    op.create_index(op.f("ix_crawl_sources_name"), "crawl_sources", ["name"], unique=False)

    op.create_table(
        "price_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("product_name", sa.String(length=128), nullable=False),
        sa.Column("spec", sa.String(length=128), nullable=True),
        sa.Column("material", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("change_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("tax_included", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "category", "region", "city", "product_name", "spec", "source_name", name="uq_price_daily_natural"),
    )
    op.create_index(op.f("ix_price_daily_category"), "price_daily", ["category"], unique=False)
    op.create_index(op.f("ix_price_daily_city"), "price_daily", ["city"], unique=False)
    op.create_index(op.f("ix_price_daily_date"), "price_daily", ["date"], unique=False)
    op.create_index(op.f("ix_price_daily_id"), "price_daily", ["id"], unique=False)
    op.create_index(op.f("ix_price_daily_product_name"), "price_daily", ["product_name"], unique=False)
    op.create_index(op.f("ix_price_daily_region"), "price_daily", ["region"], unique=False)
    op.create_index(op.f("ix_price_daily_source_name"), "price_daily", ["source_name"], unique=False)

    op.create_table(
        "crawl_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("keyword", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_saved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["crawl_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_tasks_id"), "crawl_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_crawl_tasks_keyword"), "crawl_tasks", ["keyword"], unique=False)
    op.create_index(op.f("ix_crawl_tasks_source_id"), "crawl_tasks", ["source_id"], unique=False)
    op.create_index(op.f("ix_crawl_tasks_status"), "crawl_tasks", ["status"], unique=False)

    op.create_table(
        "scaffold_bid_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=True),
        sa.Column("project_name", sa.String(length=512), nullable=False),
        sa.Column("province", sa.String(length=64), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("district", sa.String(length=64), nullable=True),
        sa.Column("buyer", sa.String(length=256), nullable=True),
        sa.Column("agency", sa.String(length=256), nullable=True),
        sa.Column("winner", sa.String(length=256), nullable=True),
        sa.Column("bid_amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("announcement_type", sa.String(length=64), nullable=True),
        sa.Column("scaffold_type", sa.String(length=128), nullable=True),
        sa.Column("procurement_type", sa.String(length=128), nullable=True),
        sa.Column("service_scope", sa.Text(), nullable=True),
        sa.Column("duration_text", sa.String(length=256), nullable=True),
        sa.Column("quantity_text", sa.String(length=256), nullable=True),
        sa.Column("area_m2", sa.Numeric(14, 2), nullable=True),
        sa.Column("tonnage", sa.Numeric(14, 2), nullable=True),
        sa.Column("rental_days", sa.Integer(), nullable=True),
        sa.Column("pricing_method", sa.String(length=128), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(4, 2), server_default="0.0", nullable=False),
        sa.Column("review_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["raw_document_id"], ["bid_raw_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index(op.f("ix_scaffold_bid_cases_announcement_type"), "scaffold_bid_cases", ["announcement_type"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_city"), "scaffold_bid_cases", ["city"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_extraction_confidence"), "scaffold_bid_cases", ["extraction_confidence"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_id"), "scaffold_bid_cases", ["id"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_project_name"), "scaffold_bid_cases", ["project_name"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_province"), "scaffold_bid_cases", ["province"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_publish_date"), "scaffold_bid_cases", ["publish_date"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_raw_document_id"), "scaffold_bid_cases", ["raw_document_id"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_review_status"), "scaffold_bid_cases", ["review_status"], unique=False)
    op.create_index(op.f("ix_scaffold_bid_cases_scaffold_type"), "scaffold_bid_cases", ["scaffold_type"], unique=False)

    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["scaffold_bid_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_tasks_case_id"), "review_tasks", ["case_id"], unique=False)
    op.create_index(op.f("ix_review_tasks_id"), "review_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_review_tasks_status"), "review_tasks", ["status"], unique=False)

    op.create_table(
        "scaffold_price_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bid_case_id", sa.Integer(), nullable=False),
        sa.Column("price_type", sa.String(length=64), nullable=False),
        sa.Column("scaffold_type", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("calculated_unit", sa.String(length=32), nullable=False),
        sa.Column("calculated_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bid_case_id"], ["scaffold_bid_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scaffold_price_references_bid_case_id"), "scaffold_price_references", ["bid_case_id"], unique=False)
    op.create_index(op.f("ix_scaffold_price_references_confidence"), "scaffold_price_references", ["confidence"], unique=False)
    op.create_index(op.f("ix_scaffold_price_references_id"), "scaffold_price_references", ["id"], unique=False)
    op.create_index(op.f("ix_scaffold_price_references_price_type"), "scaffold_price_references", ["price_type"], unique=False)
    op.create_index(op.f("ix_scaffold_price_references_region"), "scaffold_price_references", ["region"], unique=False)
    op.create_index(op.f("ix_scaffold_price_references_scaffold_type"), "scaffold_price_references", ["scaffold_type"], unique=False)


def downgrade() -> None:
    op.drop_table("scaffold_price_references")
    op.drop_table("review_tasks")
    op.drop_table("scaffold_bid_cases")
    op.drop_table("crawl_tasks")
    op.drop_table("price_daily")
    op.drop_table("crawl_sources")
    op.drop_table("bid_raw_documents")

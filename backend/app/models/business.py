import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, JSON, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    google_place_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    yelp_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    existing_website: Mapped[str | None] = mapped_column(Text)
    website_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="discovered", nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    assets: Mapped["BusinessAsset | None"] = relationship("BusinessAsset", back_populates="business", uselist=False)
    site: Mapped["Site | None"] = relationship("Site", back_populates="business", uselist=False)
    outreach_records: Mapped[list["Outreach"]] = relationship("Outreach", back_populates="business")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="business")


class BusinessAsset(Base):
    __tablename__ = "business_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), unique=True)
    photos: Mapped[list | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    hours: Mapped[dict | None] = mapped_column(JSON)
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    reviews_summary: Mapped[str | None] = mapped_column(Text)
    social_links: Mapped[dict | None] = mapped_column(JSON)
    services: Mapped[list | None] = mapped_column(JSON)
    price_range: Mapped[str | None] = mapped_column(String(10))
    raw_google: Mapped[dict | None] = mapped_column(JSON)
    raw_yelp: Mapped[dict | None] = mapped_column(JSON)

    business: Mapped["Business"] = relationship("Business", back_populates="assets")

import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"), unique=True)
    template_used: Mapped[str] = mapped_column(String(50), nullable=False)
    vercel_url: Mapped[str | None] = mapped_column(Text)
    custom_subdomain: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    deployed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    business: Mapped["Business"] = relationship("Business", back_populates="site")

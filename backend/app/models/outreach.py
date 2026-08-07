import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Outreach(Base):
    __tablename__ = "outreach"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"))
    email_to: Mapped[str | None] = mapped_column(String(255))
    email_sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    email_status: Mapped[str | None] = mapped_column(String(20))
    form_submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    form_status: Mapped[str | None] = mapped_column(String(20))
    response_text: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    business: Mapped["Business"] = relationship("Business", back_populates="outreach_records")

import uuid
import datetime
from sqlalchemy import String, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base


class Fatwa(Base):
    __tablename__ = "fatwas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    main_category: Mapped[str] = mapped_column(String(255), nullable=False)
    sub_category: Mapped[str | None] = mapped_column(String(255), nullable=True)

    date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    date_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    source_dataset: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
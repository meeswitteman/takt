from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from takt_backend.database import Base


class Context(Base):
    __tablename__ = "context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False, default="#888888")

    item_contexts: Mapped[list["ItemContext"]] = relationship(back_populates="context", cascade="all, delete-orphan")

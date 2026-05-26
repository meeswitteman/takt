from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from takt_backend.database import Base


class VariationList(Base):
    __tablename__ = "variation_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    entries: Mapped[list["VariationEntry"]] = relationship(
        back_populates="list", cascade="all, delete-orphan", order_by="VariationEntry.position"
    )
    items: Mapped[list["Item"]] = relationship(back_populates="variation_list")


class VariationEntry(Base):
    __tablename__ = "variation_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("variation_list.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    list: Mapped["VariationList"] = relationship(back_populates="entries")

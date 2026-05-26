from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from takt_backend.database import Base


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("item.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_todo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurring_interval: Mapped[str | None] = mapped_column(String, nullable=True)
    last_done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    src: Mapped[str | None] = mapped_column(String, nullable=True)
    start_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    variation_list_id: Mapped[int | None] = mapped_column(ForeignKey("variation_list.id"), nullable=True)
    variation_mode: Mapped[str | None] = mapped_column(String, nullable=True)  # linear | random
    variation_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    children: Mapped[list["Item"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="Item.order_index"
    )
    parent: Mapped["Item | None"] = relationship(back_populates="children", remote_side="Item.id")
    item_contexts: Mapped[list["ItemContext"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    todo_logs: Mapped[list["TodoLog"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    variation_list: Mapped["VariationList | None"] = relationship(back_populates="items")


class ItemContext(Base):
    __tablename__ = "item_context"

    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)
    context_id: Mapped[int] = mapped_column(ForeignKey("context.id"), primary_key=True)

    item: Mapped["Item"] = relationship(back_populates="item_contexts")
    context: Mapped["Context"] = relationship(back_populates="item_contexts")


class TodoLog(Base):
    __tablename__ = "todo_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # DONE | UNDONE
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    variation_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    item: Mapped["Item"] = relationship(back_populates="todo_logs")

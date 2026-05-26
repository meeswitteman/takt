from datetime import datetime
from pydantic import BaseModel
from takt_backend.schemas.context import ContextOut


class ItemCreate(BaseModel):
    parent_id: int | None = None
    title: str
    description: str | None = None
    src: str | None = None
    start_note: str | None = None


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    src: str | None = None
    start_note: str | None = None


class ItemMoveRequest(BaseModel):
    parent_id: int | None = None
    order_index: int


class ItemTodoRequest(BaseModel):
    is_todo: bool


class ItemRecurringRequest(BaseModel):
    is_recurring: bool
    recurring_interval: str | None = None  # direct | daily | weekly | weekday:0-6 | monthly_first


class ItemVariationRequest(BaseModel):
    variation_list_id: int | None = None
    variation_mode: str | None = None  # linear | random
    variation_index: int = 0


class ItemDoneRequest(BaseModel):
    is_done: bool


class ItemOut(BaseModel):
    id: int
    parent_id: int | None
    title: str
    description: str | None
    order_index: int
    is_todo: bool
    is_recurring: bool
    recurring_interval: str | None
    last_done_at: datetime | None
    src: str | None
    start_note: str | None
    is_done: bool
    variation_list_id: int | None
    variation_mode: str | None
    variation_index: int
    created_at: datetime
    updated_at: datetime
    contexts: list[ContextOut] = []
    current_variation: str | None = None
    has_children: bool = False
    breadcrumb: list[str] = []

    model_config = {"from_attributes": True}


class ItemWithChildren(ItemOut):
    children: list["ItemWithChildren"] = []


class TodoDoneRequest(BaseModel):
    note: str | None = None


class TodoLogOut(BaseModel):
    id: int
    item_id: int
    item_title: str = ""
    breadcrumb: list[str] = []
    action: str
    note: str | None
    variation_value: str | None
    completed_at: datetime

    model_config = {"from_attributes": True}

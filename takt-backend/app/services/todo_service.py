import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session, selectinload
from fastapi import HTTPException
from app.models.item import Item, ItemContext, TodoLog
from app.models.context import Context
from app.services.item_service import get_item, _enrich


def _is_due(item: Item) -> bool:
    """Bepaal of een recurring item nu zichtbaar moet zijn op basis van het interval."""
    interval = item.recurring_interval
    if not interval:
        return True

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()
    last = item.last_done_at.date() if item.last_done_at else None

    if interval == "direct":
        return True
    if interval == "daily":
        return last is None or last < today
    if interval == "weekly":
        if last is None:
            return True
        return (now - item.last_done_at).days >= 7
    if interval.startswith("weekday:"):
        try:
            target = int(interval.split(":")[1])
        except (IndexError, ValueError):
            return True
        return today.weekday() == target and (last is None or last < today)
    if interval == "monthly_first":
        if last is None:
            return True
        return last.year < today.year or last.month < today.month

    return True


def _inherited_context_ids(db: Session, item: Item) -> set[int]:
    """Collect context ids from item and all ancestors."""
    ids = {ic.context_id for ic in item.item_contexts}
    current = item
    while current.parent_id is not None:
        parent = db.get(Item, current.parent_id, options=[selectinload(Item.item_contexts)])
        if parent:
            ids |= {ic.context_id for ic in parent.item_contexts}
        current = parent
    return ids


def _get_root_id(db: Session, item: Item) -> int:
    current = item
    while current.parent_id is not None:
        parent = db.get(Item, current.parent_id)
        if parent is None:
            break
        current = parent
    return current.id


def list_todos(db: Session, context_ids: list[int], root_ids: list[int]) -> list[Item]:
    query = (
        db.query(Item)
        .filter(Item.is_todo == True)
        .options(
            selectinload(Item.item_contexts).selectinload(ItemContext.context),
            selectinload(Item.variation_list),
        )
        .order_by(Item.last_done_at.asc())
    )
    items = query.all()

    if context_ids:
        ctx_set = set(context_ids)
        items = [i for i in items if _inherited_context_ids(db, i) & ctx_set]

    if root_ids:
        root_set = set(root_ids)
        items = [i for i in items if _get_root_id(db, i) in root_set]

    items = [i for i in items if not i.is_recurring or _is_due(i)]

    return [_enrich(i, db, breadcrumb=True) for i in items]


def mark_done(db: Session, item_id: int, note: str | None) -> Item:
    item = db.get(
        Item, item_id,
        options=[
            selectinload(Item.item_contexts).selectinload(ItemContext.context),
            selectinload(Item.variation_list),
        ]
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not item.is_todo:
        raise HTTPException(status_code=400, detail="Item is not a todo")

    current_variation = None
    if item.variation_list_id and item.variation_list and item.variation_list.entries:
        entries = item.variation_list.entries
        idx = item.variation_index % len(entries)
        current_variation = entries[idx].value

        if item.variation_mode == "random":
            item.variation_index = random.randint(0, len(entries) - 1)
        else:
            item.variation_index = (idx + 1) % len(entries)

    log = TodoLog(
        item_id=item_id,
        action="DONE",
        note=note,
        variation_value=current_variation,
        completed_at=datetime.utcnow(),
    )
    db.add(log)

    item.last_done_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    item.is_done = True

    if not item.is_recurring:
        item.is_todo = False

    db.commit()
    return get_item(db, item_id)


def get_history(db: Session, item_id: int) -> list[TodoLog]:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return (
        db.query(TodoLog)
        .filter(TodoLog.item_id == item_id)
        .order_by(TodoLog.completed_at.desc())
        .all()
    )

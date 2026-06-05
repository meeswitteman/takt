from collections import defaultdict
from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from fastapi import HTTPException
from takt_backend.models.item import Item, ItemContext, TodoLog
from takt_backend.models.context import Context
from takt_backend.schemas.item import ItemCreate, ItemUpdate, ItemMoveRequest, ItemTodoRequest, ItemRecurringRequest, ItemVariationRequest, ItemDoneRequest


def _load_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id, options=[selectinload(Item.item_contexts).selectinload(ItemContext.context)])
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _next_order_index(db: Session, parent_id: int | None) -> int:
    siblings = db.query(Item).filter(Item.parent_id == parent_id).all()
    return max((s.order_index for s in siblings), default=-1) + 1


def _renumber(db: Session, parent_id: int | None) -> None:
    siblings = (
        db.query(Item)
        .filter(Item.parent_id == parent_id)
        .order_by(Item.order_index)
        .all()
    )
    for i, item in enumerate(siblings):
        item.order_index = i


def _ancestor_ids(db: Session, item_id: int) -> set[int]:
    ids: set[int] = set()
    item = db.get(Item, item_id)
    while item and item.parent_id is not None:
        ids.add(item.parent_id)
        item = db.get(Item, item.parent_id)
    return ids


def _build_breadcrumb(db: Session, item: Item) -> list[str]:
    parts = []
    current = item
    while current.parent_id is not None:
        parent = db.get(Item, current.parent_id)
        if parent is None:
            break
        parts.append(parent.title)
        current = parent
    parts.reverse()
    return parts


def _enrich(item: Item, db: Session, breadcrumb: bool = False) -> Item:
    """Attach transient attributes for serialization."""
    item.contexts = [ic.context for ic in item.item_contexts]
    if item.variation_list_id and item.variation_list:
        entries = item.variation_list.entries
        if entries:
            idx = item.variation_index % len(entries)
            item.current_variation = entries[idx].value
        else:
            item.current_variation = None
    else:
        item.current_variation = None
    item.has_children = db.query(Item.id).filter(Item.parent_id == item.id).limit(1).scalar() is not None
    item.breadcrumb = _build_breadcrumb(db, item) if breadcrumb else []
    return item


def get_roots(db: Session) -> list[Item]:
    items = (
        db.query(Item)
        .filter(Item.parent_id == None)
        .options(selectinload(Item.item_contexts).selectinload(ItemContext.context))
        .order_by(Item.order_index)
        .all()
    )
    return [_enrich(i, db) for i in items]


def _variation_value(item: Item) -> str | None:
    if item.variation_list_id and item.variation_list and item.variation_list.entries:
        entries = item.variation_list.entries
        idx = item.variation_index % len(entries)
        return entries[idx].value
    return None


def _tree_node(item: Item, kept_children: list[dict]) -> dict:
    """Bouw een ItemWithChildren-dict voor een (al geladen) item."""
    return {
        "id": item.id,
        "parent_id": item.parent_id,
        "title": item.title,
        "description": item.description,
        "order_index": item.order_index,
        "is_todo": item.is_todo,
        "is_recurring": item.is_recurring,
        "recurring_interval": item.recurring_interval,
        "last_done_at": item.last_done_at,
        "src": item.src,
        "start_note": item.start_note,
        "is_done": item.is_done,
        "variation_list_id": item.variation_list_id,
        "variation_mode": item.variation_mode,
        "variation_index": item.variation_index,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "contexts": [ic.context for ic in item.item_contexts],
        "current_variation": _variation_value(item),
        "has_children": bool(kept_children),
        "breadcrumb": [],
        "children": kept_children,
    }


def get_tree(
    db: Session,
    context_ids: list[int] | None = None,
    root_ids: list[int] | None = None,
    hide_done: bool = False,
) -> list[dict]:
    """Geef de geneste boom terug, gefilterd op context/project en optioneel
    met afgevinkte items verborgen.

    - Een item blijft staan als het zelf (of een voorouder) de gekozen context
      heeft, of als er onder het item een treffer zit (pad naar treffer).
    - `hide_done` verbergt afgevinkte items (en daarmee hun subtak).
    """
    all_items = (
        db.query(Item)
        .options(
            selectinload(Item.item_contexts).selectinload(ItemContext.context),
            selectinload(Item.variation_list),
        )
        .order_by(Item.order_index)
        .all()
    )
    by_parent: dict[int | None, list[Item]] = defaultdict(list)
    for it in all_items:
        by_parent[it.parent_id].append(it)

    ctx_set = set(context_ids) if context_ids else None
    root_set = set(root_ids) if root_ids else None

    def build(item: Item, ancestor_match: bool) -> dict | None:
        if hide_done and item.is_done:
            return None
        direct = ctx_set is not None and bool(
            {ic.context_id for ic in item.item_contexts} & ctx_set
        )
        match = ancestor_match or direct
        kept = [
            node
            for child in by_parent.get(item.id, [])
            if (node := build(child, match)) is not None
        ]
        if ctx_set is not None and not match and not kept:
            return None
        return _tree_node(item, kept)

    roots = by_parent.get(None, [])
    if root_set is not None:
        roots = [r for r in roots if r.id in root_set]
    return [node for r in roots if (node := build(r, False)) is not None]


def get_children(db: Session, item_id: int) -> list[Item]:
    _load_item(db, item_id)
    items = (
        db.query(Item)
        .filter(Item.parent_id == item_id)
        .options(selectinload(Item.item_contexts).selectinload(ItemContext.context))
        .order_by(Item.order_index)
        .all()
    )
    return [_enrich(i, db) for i in items]


def get_item(db: Session, item_id: int) -> Item:
    item = _load_item(db, item_id)
    return _enrich(item, db)


def create_item(db: Session, data: ItemCreate) -> Item:
    parent = _load_item(db, data.parent_id) if data.parent_id is not None else None
    order_index = _next_order_index(db, data.parent_id)
    item = Item(
        parent_id=data.parent_id,
        title=data.title,
        description=data.description,
        src=data.src,
        start_note=data.start_note,
        order_index=order_index,
        is_todo=True,   # nieuw item is een leaf en wordt standaard een todo
    )
    db.add(item)
    # Een ouder is geen leaf meer en kan dus geen todo blijven.
    if parent is not None and parent.is_todo:
        parent.is_todo = False
        parent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return get_item(db, item.id)


def update_item(db: Session, item_id: int, data: ItemUpdate) -> Item:
    item = _load_item(db, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    db.commit()
    return get_item(db, item_id)


def move_item(db: Session, item_id: int, data: ItemMoveRequest) -> Item:
    item = _load_item(db, item_id)

    if data.parent_id is not None:
        if data.parent_id == item_id or data.parent_id in _ancestor_ids(db, data.parent_id):
            raise HTTPException(status_code=400, detail="Cannot move item into its own subtree")
        _load_item(db, data.parent_id)

    old_parent = item.parent_id
    item.parent_id = data.parent_id

    # De nieuwe ouder is geen leaf meer en kan dus geen todo blijven.
    if data.parent_id is not None:
        new_parent = db.get(Item, data.parent_id)
        if new_parent and new_parent.is_todo:
            new_parent.is_todo = False
            new_parent.updated_at = datetime.utcnow()

    siblings = (
        db.query(Item)
        .filter(Item.parent_id == data.parent_id, Item.id != item_id)
        .order_by(Item.order_index)
        .all()
    )
    target = max(0, min(data.order_index, len(siblings)))
    siblings.insert(target, item)
    for i, s in enumerate(siblings):
        s.order_index = i

    item.updated_at = datetime.utcnow()
    db.commit()

    if old_parent != data.parent_id:
        _renumber(db, old_parent)
        db.commit()

    return get_item(db, item_id)


def set_todo(db: Session, item_id: int, data: ItemTodoRequest) -> Item:
    item = _load_item(db, item_id)
    item.is_todo = data.is_todo
    item.updated_at = datetime.utcnow()
    db.commit()
    return get_item(db, item_id)


def set_recurring(db: Session, item_id: int, data: ItemRecurringRequest) -> Item:
    item = _load_item(db, item_id)
    item.is_recurring = data.is_recurring
    item.recurring_interval = data.recurring_interval if data.is_recurring else None
    item.updated_at = datetime.utcnow()
    db.commit()
    return get_item(db, item_id)


def delete_item(db: Session, item_id: int) -> None:
    item = _load_item(db, item_id)
    parent_id = item.parent_id
    db.delete(item)
    db.commit()
    _renumber(db, parent_id)
    db.commit()


def _set_done_recursive(db: Session, item: Item, is_done: bool) -> None:
    item.is_done = is_done
    item.updated_at = datetime.utcnow()
    children = db.query(Item).filter(Item.parent_id == item.id).all()
    for child in children:
        _set_done_recursive(db, child, is_done)


def set_done(db: Session, item_id: int, data: ItemDoneRequest) -> Item:
    item = _load_item(db, item_id)
    _set_done_recursive(db, item, data.is_done)
    db.commit()
    return get_item(db, item_id)


def set_variation(db: Session, item_id: int, data: ItemVariationRequest) -> Item:
    item = _load_item(db, item_id)
    item.variation_list_id = data.variation_list_id
    item.variation_mode = data.variation_mode if data.variation_list_id else None
    item.variation_index = data.variation_index
    item.updated_at = datetime.utcnow()
    db.commit()
    return get_item(db, item_id)


def set_contexts(db: Session, item_id: int, context_ids: list[int]) -> Item:
    item = _load_item(db, item_id)
    contexts = db.query(Context).filter(Context.id.in_(context_ids)).all()
    if len(contexts) != len(context_ids):
        raise HTTPException(status_code=404, detail="One or more contexts not found")
    for ic in item.item_contexts:
        db.delete(ic)
    db.flush()
    for ctx in contexts:
        db.add(ItemContext(item_id=item_id, context_id=ctx.id))
    item.updated_at = datetime.utcnow()
    db.commit()
    return get_item(db, item_id)

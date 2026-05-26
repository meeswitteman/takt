from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from takt_backend.database import get_db
from takt_backend.schemas.item import (
    ItemCreate, ItemUpdate, ItemOut, ItemMoveRequest,
    ItemTodoRequest, ItemRecurringRequest, ItemVariationRequest, ItemDoneRequest,
)
from takt_backend.services import item_service

router = APIRouter(prefix="/api/v1/items", tags=["items"])


@router.get("", response_model=list[ItemOut])
def get_roots(db: Session = Depends(get_db)):
    return item_service.get_roots(db)


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return item_service.get_item(db, item_id)


@router.get("/{item_id}/children", response_model=list[ItemOut])
def get_children(item_id: int, db: Session = Depends(get_db)):
    return item_service.get_children(db, item_id)


@router.post("", response_model=ItemOut, status_code=201)
def create_item(data: ItemCreate, db: Session = Depends(get_db)):
    return item_service.create_item(db, data)


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db)):
    return item_service.update_item(db, item_id, data)


@router.patch("/{item_id}/move", response_model=ItemOut)
def move_item(item_id: int, data: ItemMoveRequest, db: Session = Depends(get_db)):
    return item_service.move_item(db, item_id, data)


@router.patch("/{item_id}/todo", response_model=ItemOut)
def set_todo(item_id: int, data: ItemTodoRequest, db: Session = Depends(get_db)):
    return item_service.set_todo(db, item_id, data)


@router.patch("/{item_id}/recurring", response_model=ItemOut)
def set_recurring(item_id: int, data: ItemRecurringRequest, db: Session = Depends(get_db)):
    return item_service.set_recurring(db, item_id, data)


@router.patch("/{item_id}/done", response_model=ItemOut)
def set_done(item_id: int, data: ItemDoneRequest, db: Session = Depends(get_db)):
    return item_service.set_done(db, item_id, data)


@router.patch("/{item_id}/variation", response_model=ItemOut)
def set_variation(item_id: int, data: ItemVariationRequest, db: Session = Depends(get_db)):
    return item_service.set_variation(db, item_id, data)


@router.put("/{item_id}/contexts", response_model=ItemOut)
def set_contexts(item_id: int, context_ids: list[int], db: Session = Depends(get_db)):
    return item_service.set_contexts(db, item_id, context_ids)


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item_service.delete_item(db, item_id)

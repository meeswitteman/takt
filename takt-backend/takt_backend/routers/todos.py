from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from takt_backend.database import get_db
from takt_backend.schemas.item import ItemOut, TodoDoneRequest, TodoLogOut
from takt_backend.services import todo_service

router = APIRouter(prefix="/api/v1/todos", tags=["todos"])


@router.get("", response_model=list[ItemOut])
def list_todos(
    context_id: list[int] = Query(default=[]),
    root_id: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
):
    return todo_service.list_todos(db, context_id, root_id)


@router.post("/{item_id}/done", response_model=ItemOut)
def mark_done(item_id: int, data: TodoDoneRequest, db: Session = Depends(get_db)):
    return todo_service.mark_done(db, item_id, data.note)


@router.get("/history", response_model=list[TodoLogOut])
def list_history(db: Session = Depends(get_db)):
    return todo_service.list_history(db)


@router.delete("/history")
def delete_history(
    before: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    deleted = todo_service.delete_history(db, before)
    return {"deleted": deleted}


@router.delete("/history/{log_id}", status_code=204)
def delete_history_entry(log_id: int, db: Session = Depends(get_db)):
    todo_service.delete_history_entry(db, log_id)


@router.get("/{item_id}/history", response_model=list[TodoLogOut])
def get_history(item_id: int, db: Session = Depends(get_db)):
    return todo_service.get_history(db, item_id)

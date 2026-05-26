from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.item import ItemOut, TodoDoneRequest, TodoLogOut
from app.services import todo_service

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


@router.get("/{item_id}/history", response_model=list[TodoLogOut])
def get_history(item_id: int, db: Session = Depends(get_db)):
    return todo_service.get_history(db, item_id)

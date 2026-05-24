from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.context import ContextCreate, ContextUpdate, ContextOut
from app.services import context_service

router = APIRouter(prefix="/api/v1/contexts", tags=["contexts"])


@router.get("", response_model=list[ContextOut])
def list_contexts(db: Session = Depends(get_db)):
    return context_service.list_contexts(db)


@router.post("", response_model=ContextOut, status_code=201)
def create_context(data: ContextCreate, db: Session = Depends(get_db)):
    return context_service.create_context(db, data)


@router.patch("/{context_id}", response_model=ContextOut)
def update_context(context_id: int, data: ContextUpdate, db: Session = Depends(get_db)):
    return context_service.update_context(db, context_id, data)


@router.delete("/{context_id}", status_code=204)
def delete_context(context_id: int, db: Session = Depends(get_db)):
    context_service.delete_context(db, context_id)

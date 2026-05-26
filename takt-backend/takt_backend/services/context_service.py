from sqlalchemy.orm import Session
from fastapi import HTTPException
from takt_backend.models.context import Context
from takt_backend.schemas.context import ContextCreate, ContextUpdate


def list_contexts(db: Session) -> list[Context]:
    return db.query(Context).order_by(Context.name).all()


def create_context(db: Session, data: ContextCreate) -> Context:
    if db.query(Context).filter(Context.name == data.name).first():
        raise HTTPException(status_code=409, detail=f"Context '{data.name}' already exists")
    context = Context(name=data.name, color=data.color)
    db.add(context)
    db.commit()
    db.refresh(context)
    return context


def update_context(db: Session, context_id: int, data: ContextUpdate) -> Context:
    context = db.get(Context, context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    context.name = data.name
    context.color = data.color
    db.commit()
    db.refresh(context)
    return context


def delete_context(db: Session, context_id: int) -> None:
    context = db.get(Context, context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    db.delete(context)
    db.commit()

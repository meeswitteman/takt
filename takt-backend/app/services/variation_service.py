from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.variation import VariationList, VariationEntry
from app.schemas.variation import VariationListCreate, VariationEntriesUpdate


def list_variations(db: Session) -> list[VariationList]:
    return db.query(VariationList).order_by(VariationList.name).all()


def get_variation(db: Session, list_id: int) -> VariationList:
    vl = db.get(VariationList, list_id)
    if not vl:
        raise HTTPException(status_code=404, detail="VariationList not found")
    return vl


def create_variation_list(db: Session, data: VariationListCreate) -> VariationList:
    if db.query(VariationList).filter(VariationList.name == data.name).first():
        raise HTTPException(status_code=409, detail=f"VariationList '{data.name}' already exists")
    vl = VariationList(name=data.name)
    db.add(vl)
    db.commit()
    db.refresh(vl)
    return vl


def update_entries(db: Session, list_id: int, data: VariationEntriesUpdate) -> VariationList:
    vl = get_variation(db, list_id)
    for entry in vl.entries:
        db.delete(entry)
    db.flush()
    for i, value in enumerate(data.values):
        db.add(VariationEntry(list_id=list_id, position=i, value=value))
    db.commit()
    db.refresh(vl)
    return vl


def delete_variation_list(db: Session, list_id: int) -> None:
    vl = get_variation(db, list_id)
    db.delete(vl)
    db.commit()

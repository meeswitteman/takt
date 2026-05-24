from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.variation import VariationListCreate, VariationListOut, VariationEntriesUpdate
from app.services import variation_service

router = APIRouter(prefix="/api/v1/variations", tags=["variations"])


@router.get("", response_model=list[VariationListOut])
def list_variations(db: Session = Depends(get_db)):
    return variation_service.list_variations(db)


@router.get("/{list_id}", response_model=VariationListOut)
def get_variation(list_id: int, db: Session = Depends(get_db)):
    return variation_service.get_variation(db, list_id)


@router.post("", response_model=VariationListOut, status_code=201)
def create_variation_list(data: VariationListCreate, db: Session = Depends(get_db)):
    return variation_service.create_variation_list(db, data)


@router.put("/{list_id}/entries", response_model=VariationListOut)
def update_entries(list_id: int, data: VariationEntriesUpdate, db: Session = Depends(get_db)):
    return variation_service.update_entries(db, list_id, data)


@router.delete("/{list_id}", status_code=204)
def delete_variation_list(list_id: int, db: Session = Depends(get_db)):
    variation_service.delete_variation_list(db, list_id)

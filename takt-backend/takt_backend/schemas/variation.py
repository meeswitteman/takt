from pydantic import BaseModel


class VariationEntryOut(BaseModel):
    id: int
    position: int
    value: str

    model_config = {"from_attributes": True}


class VariationListCreate(BaseModel):
    name: str


class VariationListOut(BaseModel):
    id: int
    name: str
    entries: list[VariationEntryOut] = []

    model_config = {"from_attributes": True}


class VariationEntriesUpdate(BaseModel):
    values: list[str]

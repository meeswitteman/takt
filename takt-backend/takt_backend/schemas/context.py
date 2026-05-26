from pydantic import BaseModel, field_validator
import re


class ContextCreate(BaseModel):
    name: str
    color: str = "#888888"

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("color must be a hex color like #rrggbb")
        return v


class ContextUpdate(BaseModel):
    name: str
    color: str

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("color must be a hex color like #rrggbb")
        return v


class ContextOut(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}

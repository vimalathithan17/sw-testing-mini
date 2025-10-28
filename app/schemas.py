from pydantic import BaseModel, Field, PositiveInt, field_validator
from pydantic.config import ConfigDict
from typing import Optional
from decimal import Decimal

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default="user")
    password: Optional[str] = Field(default=None)

class UserRead(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    role: str = "user"

    model_config = ConfigDict(from_attributes=True)


class UserDetail(UserRead):
    orders: list["OrderRead"] = []

class OrderCreate(BaseModel):
    user_id: PositiveInt
    amount: Decimal = Field(..., gt=Decimal("-0.01"))

    @field_validator("amount")
    def non_negative(cls, v: Decimal):
        if v < 0:
            raise ValueError("amount must be non-negative")
        # Do not quantize here; business logic will round using HALF_UP
        return v

class OrderRead(BaseModel):
    id: int
    user_id: int
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


# finalize forward refs
UserDetail.model_rebuild()

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserOut(BaseModel):
    id: int
    telegram_id: int
    email: EmailStr
    name: str
    phone: str
    created_at: datetime

    class Config:
        orm_mode = True

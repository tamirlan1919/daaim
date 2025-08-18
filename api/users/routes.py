from fastapi import APIRouter, Depends, HTTPException
from typing import List
from . import schemas

router = APIRouter(
    prefix="/users",
    tags=["Пользователи 👥"],
)


@router.get("/", response_model=List[schemas.UserOut])
async def list_users():
    return {'users': 'четко'}  # Placeholder for user list




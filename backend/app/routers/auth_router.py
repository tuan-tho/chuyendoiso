# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from fastapi.security import OAuth2PasswordRequestForm  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from ..database import get_db
from ..schemas import UserCreate, UserOut, Token
from ..crud.users import create_user, authenticate
from ..auth_utils import create_access_token
from ..deps import get_current_user

router = APIRouter(tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    # ✅ tạo payload rồi sinh token
    payload = {"sub": user.username, "user_id": user.id, "role": user.role}
    token = create_access_token(payload)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserOut)
def users_me(current_user = Depends(get_current_user)):
    return current_user

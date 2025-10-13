from sqlalchemy.orm import Session # type: ignore
from typing import Optional
from ..models import User
from ..schemas import UserCreate
from ..auth_utils import hash_password, verify_password, create_access_token  # nếu cần


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user_in: UserCreate) -> User:
    if get_user_by_username(db, user_in.username):
        raise ValueError("Username already registered")
    u = User(
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=user_in.role or "student",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    u = get_user_by_username(db, username)
    if not u:
        return None
    if not verify_password(password, u.hashed_password):
        return None
    return u

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from auth import create_access_token, password_hash
from database import get_session
from models import TokenResponse, User, UserLogin, UserRegister

router = APIRouter(prefix="/api", tags=["帳號驗證"])


@router.post("/register")
def register(payload: UserRegister, session: Session = Depends(get_session)):
    exists = session.exec(select(User).where(User.username == payload.username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="此帳號已被註冊")

    new_user = User(
        username=payload.username,
        hashed_password=password_hash.hash(payload.password),
        role=payload.role,
    )
    session.add(new_user)
    session.commit()
    return {"message": "註冊成功，請使用新帳號登入"}


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not password_hash.verify(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_access_token(user)
    return TokenResponse(access_token=token, username=user.username, role=user.role)
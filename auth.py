from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlmodel import Session, select

from database import get_session
from models import Role, User

SECRET_KEY = "change-this-to-a-random-secret-key-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

password_hash = PasswordHash.recommended()
security = HTTPBearer()


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user.username,
        "role": user.role.value,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的憑證")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登入已過期或無效，請重新登入")

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="使用者不存在")
    return user


def require_author(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.AUTHOR:
        raise HTTPException(status_code=403, detail="僅限「作者」角色執行此操作")
    return current_user


def require_editor(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.EDITOR:
        raise HTTPException(status_code=403, detail="僅限「編輯」角色執行此操作")
    return current_user
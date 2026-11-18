from enum import Enum
from typing import Optional
from pydantic import BaseModel
from sqlmodel import Field, SQLModel


# ================= 列舉定義 =================

class Role(str, Enum):
    AUTHOR = "author"
    EDITOR = "editor"


class SubmissionStatus(str, Enum):
    EDITING = "編輯中"
    REVIEWING = "審查中"
    APPROVED = "已通過"


# ================= 資料庫資料表 (Tables) =================

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, min_length=2, description="登入帳號")
    hashed_password: str = Field(description="加密後的密碼")
    role: Role = Field(description="角色: author 或 editor")


class SubmissionBase(SQLModel):
    category: str = Field(min_length=1, description="類別")
    title: str = Field(min_length=1, description="標題")
    content: str = Field(min_length=1, description="文章內容")


class Submission(SubmissionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="user.id", index=True, description="作者 ID")
    author_name: str = Field(description="作者帳號名稱")
    status: SubmissionStatus = Field(default=SubmissionStatus.EDITING, description="審查狀態")


# ================= API 請求與回應 Schema =================

class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=30)
    password: str = Field(min_length=4)
    role: Role


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: Role


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionUpdate(SubmissionBase):
    pass
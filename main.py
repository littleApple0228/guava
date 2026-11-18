from contextlib import asynccontextmanager
from enum import Enum
from typing import Optional
from urllib.parse import unquote
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, Session, SQLModel, create_engine, select


# 1. 定義角色與稿件狀態
class Role(str, Enum):
    AUTHOR = "author"
    EDITOR = "editor"


class SubmissionStatus(str, Enum):
    EDITING = "編輯中"
    REVIEWING = "審查中"
    APPROVED = "已通過"


# 2. 定義資料表與欄位規則
class SubmissionBase(SQLModel):
    category: str = Field(min_length=1, description="類別")
    title: str = Field(min_length=1, description="標題")
    content: str = Field(min_length=1, description="文章內容")


class Submission(SubmissionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    author_name: str = Field(index=True, description="作者名稱")
    status: SubmissionStatus = Field(default=SubmissionStatus.EDITING, description="審查狀態")


class SubmissionCreate(SubmissionBase):
    pass


class SubmissionUpdate(SubmissionBase):
    pass


# 3. 資料庫連線設定 (會自動產生 submissions.db 檔案)
sqlite_url = "sqlite:///submissions.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title="投稿審查平台 API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


# 4. 身分驗證與權限檢查
def get_current_user(
    x_role: Role = Header(..., description="角色: author 或 editor"),
    x_user: str = Header(..., description="使用者名稱"),
):
    return {"role": x_role, "username": unquote(x_user)}


def require_author(user: dict = Depends(get_current_user)):
    if user["role"] != Role.AUTHOR:
        raise HTTPException(status_code=403, detail="僅限「作者」角色執行此操作")
    return user


def require_editor(user: dict = Depends(get_current_user)):
    if user["role"] != Role.EDITOR:
        raise HTTPException(status_code=403, detail="僅限「編輯」角色執行此操作")
    return user


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("static/index.html")


# ================= 作者功能 API =================

@app.get("/api/author/submissions", response_model=list[Submission], tags=["作者功能"])
def list_author_submissions(
    session: Session = Depends(get_session),
    user: dict = Depends(require_author),
):
    statement = select(Submission).where(Submission.author_name == user["username"])
    return session.exec(statement).all()


@app.post("/api/author/submissions", response_model=Submission, tags=["作者功能"])
def create_submission(
    payload: SubmissionCreate,
    session: Session = Depends(get_session),
    user: dict = Depends(require_author),
):
    db_item = Submission(
        **payload.model_dump(),
        author_name=user["username"],
        status=SubmissionStatus.EDITING,
    )
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.put("/api/author/submissions/{submission_id}", response_model=Submission, tags=["作者功能"])
def update_submission(
    submission_id: int,
    payload: SubmissionUpdate,
    session: Session = Depends(get_session),
    user: dict = Depends(require_author),
):
    item = session.get(Submission, submission_id)
    if not item or item.author_name != user["username"]:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.EDITING:
        raise HTTPException(status_code=400, detail="僅「編輯中」的稿件可以修改")

    item.category = payload.category
    item.title = payload.title
    item.content = payload.content
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/api/author/submissions/{submission_id}", tags=["作者功能"])
def delete_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    user: dict = Depends(require_author),
):
    item = session.get(Submission, submission_id)
    if not item or item.author_name != user["username"]:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.EDITING:
        raise HTTPException(status_code=400, detail="僅能刪除「編輯中」的稿件")

    session.delete(item)
    session.commit()
    return {"message": "稿件已刪除"}


@app.patch("/api/author/submissions/{submission_id}/submit", response_model=Submission, tags=["作者功能"])
def submit_for_review(
    submission_id: int,
    session: Session = Depends(get_session),
    user: dict = Depends(require_author),
):
    item = session.get(Submission, submission_id)
    if not item or item.author_name != user["username"]:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.EDITING:
        raise HTTPException(status_code=400, detail="只有「編輯中」的稿件可以送出審查")

    item.status = SubmissionStatus.REVIEWING
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# ================= 編輯功能 API =================

@app.get("/api/editor/submissions", response_model=list[Submission], tags=["編輯功能"])
def list_pending_submissions(
    session: Session = Depends(get_session),
    user: dict = Depends(require_editor),
):
    statement = select(Submission).where(Submission.status == SubmissionStatus.REVIEWING)
    return session.exec(statement).all()


@app.get("/api/editor/submissions/{submission_id}", response_model=Submission, tags=["編輯功能"])
def get_submission_detail(
    submission_id: int,
    session: Session = Depends(get_session),
    user: dict = Depends(require_editor),
):
    item = session.get(Submission, submission_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    return item


@app.patch("/api/editor/submissions/{submission_id}/approve", response_model=Submission, tags=["編輯功能"])
def approve_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    user: dict = Depends(require_editor),
):
    item = session.get(Submission, submission_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.REVIEWING:
        raise HTTPException(status_code=400, detail="僅能審核「審查中」的稿件")

    item.status = SubmissionStatus.APPROVED
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.patch("/api/editor/submissions/{submission_id}/reject", response_model=Submission, tags=["編輯功能"])
def reject_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    user: dict = Depends(require_editor),
):
    item = session.get(Submission, submission_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.REVIEWING:
        raise HTTPException(status_code=400, detail="僅能退回「審查中」的稿件")

    item.status = SubmissionStatus.EDITING
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
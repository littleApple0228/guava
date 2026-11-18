from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, select

from auth import password_hash
from database import engine
from models import Role, User
from routers import author, editor, users


def seed_default_users():
    """若資料庫尚無任何帳號，自動建立 3 組測試帳號"""
    with Session(engine) as session:
        existing = session.exec(select(User)).first()
        if not existing:
            default_users = [
                User(username="wang", hashed_password=password_hash.hash("1234"), role=Role.AUTHOR),
                User(username="lee", hashed_password=password_hash.hash("1234"), role=Role.AUTHOR),
                User(username="chen", hashed_password=password_hash.hash("1234"), role=Role.EDITOR),
            ]
            session.add_all(default_users)
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    seed_default_users()
    yield


app = FastAPI(title="投稿審查平台 API", lifespan=lifespan)

# 掛載各模組路由
app.include_router(users.router)
app.include_router(author.router)
app.include_router(editor.router)

# 掛載前端靜態網頁
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("static/index.html")
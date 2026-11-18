from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from auth import require_author
from database import get_session
from models import Submission, SubmissionCreate, SubmissionStatus, SubmissionUpdate, User

router = APIRouter(prefix="/api/author", tags=["作者功能"])


@router.get("/submissions", response_model=list[Submission])
def list_author_submissions(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_author),
):
    statement = select(Submission).where(Submission.author_id == current_user.id)
    return session.exec(statement).all()


@router.post("/submissions", response_model=Submission)
def create_submission(
    payload: SubmissionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_author),
):
    db_item = Submission(
        **payload.model_dump(),
        author_id=current_user.id,
        author_name=current_user.username,
        status=SubmissionStatus.EDITING,
    )
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@router.put("/submissions/{submission_id}", response_model=Submission)
def update_submission(
    submission_id: int,
    payload: SubmissionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_author),
):
    item = session.get(Submission, submission_id)
    if not item or item.author_id != current_user.id:
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


@router.delete("/submissions/{submission_id}")
def delete_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_author),
):
    item = session.get(Submission, submission_id)
    if not item or item.author_id != current_user.id:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.EDITING:
        raise HTTPException(status_code=400, detail="僅能刪除「編輯中」的稿件")

    session.delete(item)
    session.commit()
    return {"message": "稿件已刪除"}


@router.patch("/submissions/{submission_id}/submit", response_model=Submission)
def submit_for_review(
    submission_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_author),
):
    item = session.get(Submission, submission_id)
    if not item or item.author_id != current_user.id:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    if item.status != SubmissionStatus.EDITING:
        raise HTTPException(status_code=400, detail="只有「編輯中」的稿件可以送出審查")

    item.status = SubmissionStatus.REVIEWING
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
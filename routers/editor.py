from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from auth import require_editor
from database import get_session
from models import Submission, SubmissionStatus, User

router = APIRouter(prefix="/api/editor", tags=["編輯功能"])


@router.get("/submissions", response_model=list[Submission])
def list_pending_submissions(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    statement = select(Submission).where(Submission.status == SubmissionStatus.REVIEWING)
    return session.exec(statement).all()


@router.get("/submissions/{submission_id}", response_model=Submission)
def get_submission_detail(
    submission_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    item = session.get(Submission, submission_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該稿件")
    return item


@router.patch("/submissions/{submission_id}/approve", response_model=Submission)
def approve_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
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


@router.patch("/submissions/{submission_id}/reject", response_model=Submission)
def reject_submission(
    submission_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
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
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import connection
from src.config.settings import ARTIFACTS
from src.constants.enums import Review, Role, Status
from src.controllers.auth import allow, current
from src.domain.spec import SPEC
from src.models.identity import User
from src.models.jobs import Run
from src.models.source import Dataset
from src.schemas.requests import ReviewRequest, RunRequest
from src.services.audit import record
from src.services.validation import normalize_params
from src.utils import views
from src.utils.wakeup import wake

router = APIRouter(prefix='/runs')


def require_job(db, run_id, lock=False):
    item = db.get(Run, run_id, with_for_update=lock)
    if not item:
        raise HTTPException(404, '找不到该运行记录')
    return item


@router.get('')
def index(db: Session = Depends(connection), actor: User = Depends(current)):
    return [views.run(item) for item in db.scalars(select(Run).order_by(Run.id.desc()).limit(100))]


@router.post('', status_code=202)
def create(body: RunRequest, db: Session = Depends(connection),
           actor: User = Depends(allow(Role.ADMIN, Role.ANALYST))):
    if not db.get(Dataset, body.dataset_id):
        raise HTTPException(404, '找不到指定的数据批次')
    item = Run(name=body.name, dataset_id=body.dataset_id, params=normalize_params(body.params), author=actor.username)
    db.add(item)
    db.flush()
    record(db, actor.username, 'analysis.queued', item.id, dataset_id=item.dataset_id)
    db.commit()
    wake()
    return views.run(item, detail=True)


@router.get('/{run_id}')
def detail(run_id: int, db: Session = Depends(connection), actor: User = Depends(current)):
    return views.run(require_job(db, run_id), detail=True)


@router.get('/{run_id}/export')
def export(run_id: int, db: Session = Depends(connection), actor: User = Depends(current)):
    item = require_job(db, run_id)
    if not item.export_file:
        raise HTTPException(409, '此记录尚无可下载结果')
    path = ARTIFACTS / item.export_file
    if not path.is_file():
        raise HTTPException(410, '导出文件已不可用，请重新运行')
    return FileResponse(path, media_type='text/csv', filename=f'{SPEC["short_name"]}-{item.id}.csv')


@router.post('/{run_id}/review')
def review(run_id: int, body: ReviewRequest, db: Session = Depends(connection),
           actor: User = Depends(allow(Role.ADMIN))):
    item = require_job(db, run_id, lock=True)
    if item.status != Status.COMPLETE or item.review != Review.PENDING:
        raise HTTPException(409, '只有已完成且待复核的记录可以提交决定')
    if body.review == Review.PENDING:
        raise ValueError('请选择通过或退回')
    if body.review == Review.ACCEPTED and not body.decision:
        raise ValueError('通过复核时请填写处置决定')
    modes = SPEC.get('modes')
    if modes and body.decision and body.decision not in modes:
        raise ValueError('请选择项目支持的处置决定')
    item.review, item.review_note, item.decision = body.review, body.note, body.decision or None
    record(db, actor.username, f'review.{item.review}', item.id, note=body.note, decision=item.decision)
    db.commit()
    return views.run(item, detail=True)

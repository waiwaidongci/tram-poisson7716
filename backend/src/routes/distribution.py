from datetime import UTC, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import connection
from src.constants.enums import Role
from src.controllers.auth import allow, current
from src.models.identity import User
from src.models.jobs import Delivery, Schedule
from src.models.source import Dataset
from src.schemas.requests import ScheduleRequest
from src.services.audit import record
from src.services.validation import normalize_params
from src.utils import views
from src.utils.time import now
from src.utils.wakeup import wake

router = APIRouter()


@router.get('/schedules')
def schedules(db: Session = Depends(connection), actor: User = Depends(current)):
    return [views.schedule(item) for item in db.scalars(select(Schedule).order_by(Schedule.id.desc()).limit(100))]


@router.post('/schedules', status_code=201)
def add(body: ScheduleRequest, db: Session = Depends(connection), actor: User = Depends(allow(Role.ADMIN))):
    if not db.get(Dataset, body.dataset_id):
        raise HTTPException(404, '找不到指定的数据批次')
    if body.first_at.utcoffset() is None:
        raise ValueError('首次运行时间需要明确时区')
    first = body.first_at.astimezone(UTC).replace(tzinfo=None)
    stamp = now()
    if first < stamp - timedelta(seconds=30) or first > stamp + timedelta(days=366):
        raise ValueError('请选择从现在起一年内的首次运行时间')
    item = Schedule(dataset_id=body.dataset_id, params=normalize_params(body.params), name=body.name,
                    recipient=body.recipient, next_at=first, repeat_daily=body.repeat_daily, author=actor.username)
    db.add(item)
    db.flush()
    record(db, actor.username, 'schedule.created', item.id, recipient=item.recipient)
    db.commit()
    wake()
    return views.schedule(item)


@router.post('/schedules/{schedule_id}/disable')
def disable(schedule_id: int, db: Session = Depends(connection), actor: User = Depends(allow(Role.ADMIN))):
    item = db.get(Schedule, schedule_id, with_for_update=True)
    if not item:
        raise HTTPException(404, '找不到该分发计划')
    if item.enabled:
        item.enabled = False
        record(db, actor.username, 'schedule.disabled', item.id)
        db.commit()
    return views.schedule(item)


@router.get('/deliveries')
def outbox(db: Session = Depends(connection), actor: User = Depends(current)):
    return [views.delivery(item) for item in db.scalars(select(Delivery).order_by(Delivery.id.desc()).limit(100))]

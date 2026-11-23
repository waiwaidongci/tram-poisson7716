from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import connection
from src.constants.enums import Role
from src.controllers.auth import allow, current
from src.models.identity import Audit, User
from src.schemas.requests import Credentials
from src.services.audit import record
from src.utils.security import hash_password, matches, token
from src.utils.time import iso

router = APIRouter()
dummy_hash = hash_password('unknown-identity')


@router.post('/auth/login')
def login(body: Credentials, db: Session = Depends(connection)):
    actor = db.get(User, body.username)
    if not matches(body.password, actor.password_hash if actor else dummy_hash) or not actor:
        raise HTTPException(401, '账号或密码错误')
    record(db, actor.username, 'auth.login', actor.username)
    db.commit()
    return {'token': token(actor.username, actor.role), 'username': actor.username, 'role': actor.role}


@router.get('/auth/me')
def me(actor: User = Depends(current)):
    return {'username': actor.username, 'role': actor.role}


@router.get('/audit')
def audits(db: Session = Depends(connection), actor: User = Depends(allow(Role.ADMIN))):
    return [{'actor': item.actor, 'event': item.event, 'target': item.target, 'info': item.info,
             'created_at': iso(item.created_at)}
            for item in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(60))]

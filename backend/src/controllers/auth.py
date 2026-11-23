import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from src.config.database import connection
from src.models.identity import User
from src.utils.security import subject

bearer = HTTPBearer(auto_error=False)


def current(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
            db: Session = Depends(connection)):
    denied = HTTPException(401, '请先登录或重新登录', headers={'WWW-Authenticate': 'Bearer'})
    if not credentials:
        raise denied
    try:
        actor = db.get(User, subject(credentials.credentials))
    except jwt.InvalidTokenError:
        raise denied from None
    if not actor:
        raise denied
    return actor


def allow(*roles):
    def check(actor: User = Depends(current)):
        if actor.role not in roles:
            raise HTTPException(403, '当前角色没有此操作权限')
        return actor
    return check

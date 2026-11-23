from src.models.identity import Audit


def record(db, actor, event, target, **info):
    db.add(Audit(actor=actor, event=event, target=str(target), info=info))

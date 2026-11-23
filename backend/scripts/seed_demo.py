import json
from sqlalchemy import func, select
from src.config.database import Session
from src.constants.enums import Role
from src.domain.demo import demo_rows, grouped_rows
from src.domain.spec import SPEC
from src.models.identity import User
from src.models.source import Dataset
from src.services.datasets import save
from src.utils.security import hash_password


def seed():
    with Session.begin() as db:
        for role in Role:
            if not db.get(User, role.value):
                db.add(User(username=role.value, role=role, password_hash=hash_password(f'{role.value}-demo-2611')))
        item, created = save(db, SPEC['default_dataset'], SPEC['sample_name'], demo_rows(), 'seed')
        grouped, grouped_created = save(db, SPEC['grouped_default_dataset'], SPEC['grouped_sample_name'],
                                        grouped_rows(), 'seed')
        return {'users': db.scalar(select(func.count()).select_from(User)),
                'datasets': db.scalar(select(func.count()).select_from(Dataset)),
                'seed_dataset_id': item.id, 'row_count': item.row_count, 'checksum': item.checksum,
                'created_dataset': created,
                'grouped_dataset_id': grouped.id, 'grouped_row_count': grouped.row_count,
                'grouped_checksum': grouped.checksum, 'created_grouped_dataset': grouped_created}


if __name__ == '__main__':
    print(json.dumps(seed(), ensure_ascii=False))

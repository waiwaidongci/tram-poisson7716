import csv
import hashlib
import io
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.domain.demo import grouped_rows, demo_rows
from src.domain.spec import SPEC
from src.models.source import Dataset


def checksum(rows):
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def save(db, name, filename, rows, actor):
    signature = checksum(rows)
    lookup = select(Dataset).where(Dataset.name == name, Dataset.checksum == signature)
    existing = db.scalar(lookup)
    if existing:
        return existing, False
    dataset = Dataset(name=name, filename=filename, checksum=signature, rows=rows,
                      row_count=len(rows), author=actor)
    try:
        with db.begin_nested():
            db.add(dataset)
            db.flush()
    except IntegrityError:
        existing = db.scalar(lookup.with_for_update())
        if existing:
            return existing, False
        raise
    return dataset, True


def template(format='windows'):
    if format == 'grouped':
        fields = [field['key'] for field in SPEC['grouped_fields']]
        rows = grouped_rows()
    else:
        fields = [field['key'] for field in SPEC['fields']]
        rows = demo_rows()
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    # The complete representative dataset also works as a reproducible import fixture.
    writer.writerows(rows)
    return '\ufeff' + buffer.getvalue()

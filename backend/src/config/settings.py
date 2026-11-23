import os
from pathlib import Path

DB_URL = os.environ['DATABASE_URL']
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
JWT_SECRET = os.environ['JWT_SECRET']
ARTIFACTS = Path(os.environ.get('ARTIFACT_DIR', '/artifacts'))
SEED_DEMO = os.environ.get('SEED_DEMO', 'true').lower() == 'true'
QUEUE = 'analysis-wakeup'

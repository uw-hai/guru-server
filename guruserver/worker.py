import os
import celery

celery_app = celery.Celery('worker')
celery_app.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                       CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])

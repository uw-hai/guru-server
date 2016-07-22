web: gunicorn guruserver.app:app --log-file -
worker: celery worker --app=guruserver.worker.celery_app

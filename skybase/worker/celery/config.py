# global celery configuration defaults
CELERY_RESULT_PERSISTENT = 'True'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_RESULT_EXPIRES = '3600'
CELERYD_PREFETCH_MULTIPLIER = 1
CELERY_IMPORTS = ('skybase.worker.celery.tasks', 'skybase.worker.celery.state.tasks')

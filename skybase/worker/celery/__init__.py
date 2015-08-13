from __future__ import absolute_import

from celery import Celery

from skybase import config as sky_cfg

# initialize celery worker application
app = Celery('skybase')

# static configuration values
app.config_from_object('skybase.worker.celery.config')

# dynamic configuration values
worker_cfg = sky_cfg.SkyConfig.init_from_file(
    schema_name='worker',
    config_dir=sky_cfg.CONFIG_DIR,
)

# add dynamic worker configuration elements
app.conf.update(
    BROKER_URL = worker_cfg.data['BROKER_URL'],
    CELERY_RESULT_BACKEND = worker_cfg.data['CELERY_RESULT_BACKEND'],
)

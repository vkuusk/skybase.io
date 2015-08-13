from celery.utils.log import get_task_logger

from skybase.worker.celery import app
from skybase.utils import simple_error_format
import skybase.exceptions
import skybase.actions.state.local

logger = get_task_logger(__name__)

@app.task(bind=True)
def create(self, planet_name, service_name, tag, registration, provider, stacks, **kwargs):

    try:
        logger.info('attempt to instantiate update state db record ({0}, {1})'.format(id, kwargs))

        # attempt to read state db record from local resources
        result = skybase.actions.state.local.create(planet_name, service_name, tag, registration, provider, stacks, **kwargs)

    except skybase.exceptions.SkyBaseError as e:
        logger.info('failed to create ServiceRegistryRecord({0})'.format(id))
        result = simple_error_format(e)

    return result

@app.task(bind=True)
def read(self, id, **kwargs):

    try:
        logger.info('attempt to instantiate read state db record ({0}, {1})'.format(id, kwargs))

        # attempt to read state db record from local resources
        result = skybase.actions.state.local.read(id, **kwargs)

    except skybase.exceptions.SkyBaseError as e:
        logger.info('failed to instantiate ServiceRegistryRecord({0})'.format(id))
        result = simple_error_format(e)

    return result

@app.task(bind=True)
def update(self, record_id, record_object, **kwargs):

    try:
        logger.info('attempt to instantiate update state db record ({0}, {1})'.format(id, kwargs))

        # attempt to read state db record from local resources
        result = skybase.actions.state.local.update(record_id, record_object, **kwargs)

    except skybase.exceptions.SkyBaseError as e:
        logger.info('failed to instantiate ServiceRegistryRecord({0})'.format(id))
        result = simple_error_format(e)

    return result


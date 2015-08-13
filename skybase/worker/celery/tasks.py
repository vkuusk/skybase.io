from celery.utils.log import get_task_logger

from skybase.worker.celery import app
from skybase.runner import Runner
from skybase.skytask import TaskResult
from skybase.utils import simple_error_format
import skybase.exceptions

logger = get_task_logger(__name__)


@app.task(bind=True)
def execute(self, skytask_name, skytask_args, **kwargs):

    try:
        # initialize skytask from class name and submitted args
        skytask = Runner(skytask_name, skytask_args)

    except skybase.exceptions.SkyBaseError as e:
        # create a result object to handle Runner() init exceptions
        execute_result = TaskResult()
        execute_result.status = 'FAIL'
        execute_result.output = simple_error_format(e)

        logger.warning('Runner({0}) failed to instantiate: {1}'.format(skytask_name, simple_error_format(e)))

    else:
        # attempt to execute successfully created skytask
        execute_result = skytask.execute()

        if len(execute_result.next_task_name) > 0:
            # queue up next/postproc tasks
            # execute task in async mode, routing it to derived message queue

            # TODO: route to correct queue based on next_task_name and planet args if exist
            celery_result = execute.apply_async(
                args=[execute_result.next_task_name, execute_result.next_args],
                queue='admin',
                kwargs={},
            )

            logger.info('{0} next task_id: {1}'.format(skytask_name, celery_result))

    return execute_result.convert_to_string()

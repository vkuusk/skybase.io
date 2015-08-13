from skybase import exceptions as sky_e
from skybase import skytask
from skybase import config as sky_cfg


class Runner(object):

    def __init__(self, task_name=None, all_arguments=None):

        self.args = dict(all_arguments)
        self.sky_task_name = task_name

        # runner configuration directory defined by execution context:
        # restapi, worker or client in local mode
        self.runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)

        task_class = skytask.get_task_class_by_name(task_name)

        self.task = task_class(self.args, self.runner_cfg)

        self.task_result = skytask.TaskResult()

    def execute(self):
        check_result = self.task.preflight_check()
        if check_result.status == 'FAIL':
            # TODO: options needed for defining/handling complex preflight error output; some are SkyBaseError and are not JSON serializable
            self.task_result.output = str(check_result.output)

        else:
            try:
                self.task_result = self.task.execute()
            except sky_e.SkyBaseError as e:
                # TODO: push this into runner_result
                error_string = 'TASK FAILED for : ' + self.sky_task_name + ' : ' + e.message

                self.task_result.set_output(error_string)
                self.task_result.set_output_format(skytask.output_format_raw)

        return self.task_result

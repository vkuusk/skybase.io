import abc
import importlib
import json

import skybase.utils

# Result from Task execute has a type, base on type CLI can present is differently
output_format_raw = 'RAW'
output_format_json = 'JSON'

class SkyTask(object):
    # TODO: add attribute with list of execution modes
    # some tasks are local only e.g. artiball init
    # some tasks are restapi only e.g. admin adduser
    __metaclass__ = abc.ABCMeta

    def __init__(self, args, runner_cfg):

        self.result = TaskResult()
        self.preflight_check_result = TaskResult()

        self.next_task_name = ''
        self.next_args = dict()

    def presubmit_check(self, **kwargs):
        """
        This check will be executed PRIOR to the task being submitted
        this allows you to do a basic y/n style verification.

        It should raise a SkyBasePresubmitCheckError if the check
        does not pass

        NOTE: You *cannot* do validation based on data as this method
        is executed on the client not the server.

        :type kwargs: kwargs
        :param kwargs: The arguments
        """
        pass

    @abc.abstractmethod
    def execute(self, **kwargs):
        pass

    @abc.abstractmethod
    def preflight_check(self, **kwargs):
        pass


# ---- name conversions for the command line processing into real module names:
def group_command_2_class_name(group, command):
    the_name = ''

    words = command.split('_')
    for word in words:
        temp = word[0].upper() + word[1:]
        the_name += temp

    return the_name


def group_command_2_package_name():
    the_name = ''

    return the_name


def get_task_class_by_name(task_name):

    tasks_package = 'skybase.skytask'

    # Convention is that inside skytask there is "command_group" package directory and inside package it should be
    # a file with the name of the command
    # the class in camel case is defied in that file
    # full task name is
    # group.name
    # so
    # 1. task_name is used to import module
    # 2. class_name is used to get the class

    (package_name, command_name) = task_name.split('.')

    class_name = group_command_2_class_name(package_name, command_name)

    mod_name = '.'.join([tasks_package, task_name])

    task_module = importlib.import_module(mod_name)

    task_class = getattr(task_module, class_name)

    return task_class


class TaskResult(object):
    def __init__(self, a_format=output_format_raw, an_output='', a_status='SUCCESS'):

        self.output = an_output
        self.format = a_format
        self.status = a_status

        # collect arguments for the next task
        # if any
        self.next_task_name = ''
        self.next_args = dict()

    def convert_to_string(self):

        result_dict = dict()
        result_dict['output'] = self.output
        result_dict['format'] = self.format
        result_dict['status'] = self.status
        # at some point we'll do more

        result_string = json.dumps(result_dict)

        return result_string

    def from_string(self, result_string):
        result_dict = json.loads(result_string)
        self.output = result_dict['output']
        self.format = result_dict['format']
        self.status = result_dict['status']

    def print_result(self):

        if self.format == output_format_raw or self.format == '':
            print self.output

        elif self.format == output_format_json:
            json_string = skybase.utils.json_pretty_print(self.output)
            print json_string

    def set_output(self, an_output):
        self.output = an_output

    def set_output_format(self, a_format):
        self.format = a_format

    # initialized class from JSON serialized string
    @classmethod
    def init_from_json(cls, json_serialized_result):
        json_result = json.loads(json_serialized_result)
        result_format = json_result['format']
        result_output = json_result['output']
        result_status = json_result['status']
        taskresult = cls(result_format, result_output, result_status)
        return taskresult

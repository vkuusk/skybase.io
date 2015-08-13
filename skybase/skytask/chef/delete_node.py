import logging
import os
import sys
import skybase
import skybase.exceptions
from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils import user_yes_no_query
from skybase.utils.logger import Logger
from skybase.planet import Planet
from skybase.utils import simple_error_format
from skybase.actions import sky_chef as sky_chef_actions


def chef_delete_node_add_arguments(parser):
    """
    Add the arguments to the ArgParser object

    :type parser: argparse.ArgumentParser
    :param parser: The arguments
    """
    chef_delete_node = parser.add_argument_group('chef delete-node')
    chef_delete_node.add_argument(
        '-n',
        '--node',
        dest='node',
        action='store',
        default=None,
        required=True
    )
    chef_delete_node.add_argument(
        '-p',
        '--planet',
        dest='planet',
        action='store',
        default=None,
        required=True
    )
    chef_delete_node.add_argument(
        '-m',
        '--mode',
        dest='exec_mode',
        action='store',
        choices=['local', 'restapi'],
        default='restapi',
        help="execution mode [default: %(default)s]"
    )


class DeleteNode(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__))
        self.name = 'chef.delete_node'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def presubmit_check(self, **kwargs):
        if not user_yes_no_query('Are you sure you wish to delete node "%s"?' % self.args.get('node')):
            raise skybase.exceptions.SkyBasePresubmitCheckError('Aborted due to user input.')

    def preflight_check(self):
        # initialize results container
        preflight_result = []

        # instantiate planet
        try:
            self.planet = Planet(self.args.get('planet'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('planet init: {0}'.format(simple_error_format(e))))

        try:
            self.node = sky_chef_actions.get_node(self.planet, self.args.get('node'), self.logger)
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('could not find node "{0}": {1}'.format(self.args.get('node'), simple_error_format(e))))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result

    def execute(self):

        try:
            sky_chef_actions.delete_node(self.planet, self.args.get('node'), self.logger)
        except Exception as e:
            self.result.status = sky_cfg.API_STATUS_FAIL
            raise skybase.exceptions.SkyBaseResponseError('Could not delete node "{0}" from Chef: {1}'.format(self.args.get('node'), simple_error_format(e)))

        try:
            sky_chef_actions.delete_client(self.planet, self.args.get('node'), self.logger)
        except Exception as e:
            self.result.status = sky_cfg.API_STATUS_FAIL
            raise skybase.exceptions.SkyBaseResponseError('Could not delete node client "{0}" from Chef: {1}'.format(self.args.get('node'), simple_error_format(e)))

        self.result.status = sky_cfg.API_STATUS_SUCCESS
        self.result.output = 'Node "{0}" has been deleted from Chef'.format(self.args.get('node'))

        return self.result

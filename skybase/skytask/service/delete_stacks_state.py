import logging
import json

from skybase.skytask import SkyTask
from skybase.utils.logger import Logger
from skybase.actions.dbstate import delete_stacks
from skybase import skytask
from skybase.service import SkyRuntime
from skybase.planet import Planet
from skybase.utils import simple_error_format

import skybase.exceptions

def service_delete_stacks_state_add_arguments(parser):
    parser.add_argument(
        '-p', '--planet',
        dest='planet_name',
        action='store',
        required=True,
        help='planet name')

    parser.add_argument(
        '-s', '--service',
        dest='service_name',
        action='store',
        required=True,
        help='service name.')

    parser.add_argument(
        '-t', '--tag',
        dest='tag',
        action='store',
        required=True,
        help='deployment tag or continent.')

    parser.add_argument(
        '-k', '--stacks',
        dest='stacks',
        action='store',
        type=json.loads,
        required=True,
        help='stack info object')

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )


class DeleteStacksState(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'service.delete_stacks_state'
        self.args = all_args
        self.runner_cfg = runner_cfg
        self.planet = None
        self.runtime = SkyRuntime(apply=all_args.get('apply', False))

    def preflight_check(self):
        # container for preflight check issues
        preflight_result = []

        # instantiate planet
        try:
            self.planet = Planet(self.args.get('planet_name'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('planet init: {0}'.format(simple_error_format(e))))

        # TODO: test if state record id exists

        return self.preflight_check_result

    def execute(self):
        # record planet state record
        record_id = delete_stacks(
            planet_name=self.planet.planet_name,
            service_name=self.args.get('service_name'),
            tag=self.args.get('tag'),
            stacks=self.args['stacks'],
            apply=self.runtime.apply,
        )

        # prepare result object and execute query
        self.result.output = record_id
        self.result.format = skytask.output_format_json
        return self.result
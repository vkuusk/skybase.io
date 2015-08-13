import logging
import json

from skybase.skytask import SkyTask
from skybase.artiball import Artiball
from skybase.utils.logger import Logger
from skybase.actions.dbstate import write_service_state_record
from skybase import skytask
from skybase.planet import Planet
from skybase.utils import simple_error_format
import skybase.actions.skycloud
import skybase.exceptions

def service_record_state_add_arguments(parser):
    parser.add_argument(
        '-p', '--planet',
        dest='planet_name',
        action='store',
        required=True,
        help='planet name')

    parser.add_argument(
        '-a', '--artiball',
        dest='source_artiball',
        action='store',
        required=True,
        help='Packaged Release Bundle Name (required)'
    )

    parser.add_argument(
        '-r', '--provider',
        dest='provider_name',
        action='store',
        required=True,
        help='provider name')

    parser.add_argument(
        '-s', '--service',
        dest='service_name',
        action='store',
        required=True,
        help='service name.')

    parser.add_argument(
        '-d', '--deploy-tag',
        dest='deploy_tag',
        action='store',
        required=True,
        help='deployment tag.')

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


class RecordState(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'service.record_state'
        self.args = all_args
        self.runner_cfg = runner_cfg

        self.planet = None
        self.stacks = self.args['stacks']


    def preflight_check(self):
        preflight_result = []
        # instantiate planet
        try:
            self.planet = Planet(self.args.get('planet_name'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('planet init: {0}'.format(simple_error_format(e))))


        # validate stacks for errors before writing to service state registry
        try:
            are_stacks_valid = skybase.actions.skycloud.are_stacks_valid(
                self.planet.orchestration_engine,
                self.stacks)

            if not are_stacks_valid:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(skybase.exceptions.SkyBaseValidationError('cannot write service state record with invalid stacks'))

        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('test for valid stacks: {0}'.format(simple_error_format(e))))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):

        # record service state record
        record_id = write_service_state_record(
            planet_name=self.planet.planet_name,
            service_name=self.args['service_name'],
            tag=self.args['deploy_tag'],
            registration=self.args.get('registration'),
            provider=self.planet.provider,
            stacks=self.stacks,
        )

        # prepare result object and execute query
        self.result.output = record_id
        self.result.format = skytask.output_format_json

        return self.result
import logging

from skybase.skytask import SkyTask
from skybase.utils.logger import Logger
from skybase.utils import simple_error_format
from skybase import config as sky_cfg
from skybase import skytask
from skybase.planet import Planet
import skybase.exceptions

def planet_describe_add_arguments(parser):

    parser.add_argument(
        '-p', '--planet',
        dest='destination_planet',
        action='store',
        default=sky_cfg.DEFAULT_PLANET,
        help='planet name (required).'
    )

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )

class Describe(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'planet.describe'
        self.args = all_args
        self.runner_cfg = runner_cfg
        self.planet = None

    def preflight_check(self):
        preflight_result = []
        # instantiate planet
        try:
            self.planet = Planet(self.args.get('destination_planet'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('planet init: {0}'.format(simple_error_format(e))))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result

    def execute(self):
        self.result.format = skytask.output_format_json
        self.result.output = {
            self.planet.planet_name: self.planet.planet_as_dict
        }
        result = self.result
        return result


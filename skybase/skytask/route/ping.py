import logging

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger
from skybase.planet import Planet
from skybase.utils import simple_error_format

import skybase.actions.route


def route_ping_add_arguments(parser):

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )

    parser.add_argument(
        '-p', '--planet',
        dest='planet_name',
        action='store',
        default=sky_cfg.DEFAULT_PLANET,
        help='planet name'
    )

    parser.add_argument(
        '-n', '--count',
        dest='count',
        action='store',
        default=1,
        help='number of times to repeat'
    )

    parser.add_argument(
        '-s', '--sleep',
        dest='sleep_interval',
        action='store',
        default=0,
        help='interval to sleep before returning'
    )

class Ping(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'route.ping'
        self.args = all_args
        self.runner_cfg = runner_cfg


    def preflight_check(self):
        # initialize results container
        preflight_result = []

        # instantiate planet
        try:
            self.planet = Planet(self.args.get('planet_name'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('planet init: {0}'.format(simple_error_format(e))))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):

        # TODO: create standard result object
        result_dict = dict(
            data=dict(),
            type=skytask.output_format_raw,
            status=None
        )

        # ping worker number of times indicated by --count
        for n in range(int(self.args.get('count'))):
            ping_N = 'ping_{0}'.format(n)
            result_dict['data'][ping_N] = skybase.actions.route.ping(**self.args)

        # TODO: result.status will be derived from all action status values.
        self.result.status = sky_cfg.API_STATUS_SUCCESS
        self.result.format = skytask.output_format_json
        self.result.output = result_dict['data']

        return self.result



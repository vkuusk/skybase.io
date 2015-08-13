import logging

from skybase.skytask import SkyTask
from skybase.utils.logger import Logger
from skybase import skytask
from skybase.utils import simple_error_format
import skybase.config as sky_cfg
import skybase.api.state
import skybase.actions.state
import skybase.exceptions


def state_read_add_arguments(parser):

    parser.add_argument(
        '-i', '--id',
        dest='skybase_id',
        action='store',
        required=True,
        help='target skybase service registry id')

    parser.add_argument(
        '-f', '--format',
        dest='format',
        action='store',
        choices={'json', 'yaml'},
        default='json',
        help='output format'
    )

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )


class Read(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'state.read'
        self.args = all_args
        self.runner_cfg = runner_cfg
        self.mode = self.args.get('exec_mode')
        self.format = self.args.get('format')
        self.id = self.args.get('skybase_id')

    def preflight_check(self):
        return self.preflight_check_result

    def execute(self):

        # attempt to read state db record
        try:
            result = skybase.actions.state.read(
                mode=self.mode,
                record_id=self.id,
                credentials=sky_cfg.SkyConfig.init_from_file('credentials').data,
                format=self.format
            )
        except skybase.exceptions.SkyBaseError as e:
            result = simple_error_format(e)

        # set result output mode; --format default = json
        if self.format == 'yaml':
            self.result.format = skytask.output_format_raw
        else:
            self.result.format = skytask.output_format_json

        self.result.output = result

        return self.result
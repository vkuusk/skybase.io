import os
import logging

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import pack as pack_actions
from skybase.utils.logger import Logger


def pack_init_add_arguments(parser):

    parser.add_argument(
        '-d',
        '--directory',
        dest='base_dir',
        default='./',
        action='store'
    )
    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local'},
        default='local',
        help='execution mode (default local)'
    )
    parser.add_argument(
        '-f', '--force',
        dest='force',
        action='store_true',
        default=False,
        help='force override (default False)'
    )


class Init(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'pack.init'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):
        result_string = ""
        if self.args['base_dir']:
            base_dir = self.args['base_dir']
            if base_dir.split('/')[-1] is not 'skybase':
                base_dir = os.path.join(base_dir, 'skybase')
        else:
            base_dir = os.path.join(os.getcwd(), 'skybase')

        # Hardcoding default to True for pack group command, revisit later
        self.args['apply'] = True
        if self.args['apply']:
            self.logger.write('Initializing package in ' + base_dir, multi_line=False)
            result_string += pack_actions.init_from_schemas(base_dir, 'artiball', dry_run=False,
                                                            force=self.args['force'])
        else:
            self.logger.write('DRY RUN :::: Initializing package in ' + base_dir, multi_line=False)
            result_string += pack_actions.init_from_schemas(base_dir, 'artiball', dry_run=True)
        self.result.status = sky_cfg.API_STATUS_SUCCESS
        self.result.output = result_string
        return self.result

    def preflight_check(self):
        result = skytask.TaskResult()
        return result


import logging
import os

from distutils import dir_util

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import pack as pack_actions
from skybase.operands import artiball as ab_object
from skybase.utils.logger import Logger


def pack_validate_add_arguments(parser):

    parser.add_argument(
        '-d',
        '--directory',
        dest='base_dir',
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
        '--verbose',
        dest='verbose',
        action='store_true',
        default=True,
        help='retrieve details of artiball validation'
    )

class Validate(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'pack.validate'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):
        if self.args['base_dir']:
            base_dir = self.args['base_dir']
            if base_dir.split('/')[-1] is not 'skybase':
                base_dir = os.path.join(base_dir, 'skybase')
        else:
            base_dir = os.path.join(os.getcwd(), 'skybase')

        if self.args['verbose']:
            self.logger.write('Validating package in ' + base_dir, multi_line=False)

        if not os.path.exists(os.path.join(base_dir, 'app')):
            dir_util.mkpath(os.path.join(base_dir, 'app'))
        validate_result = pack_actions.validate_with_schema(base_dir, 'artiball')
        artiball = ab_object.Artiball(base_dir)
        artiball.update_content()
        artiball.create_manifest_file()
        if (artiball.chef_repo is None) and \
                (os.listdir(os.path.join(base_dir, 'installation', 'chef', 'cookbooks')) == []) and \
                artiball.cookbooks:
                self.result.output += "Cannot render cookbooks. Please specify git repository URL in skybase.yaml " \
                                      "or make sure cookbooks are in " + \
                                      os.path.join(base_dir, 'installation', 'chef', 'cookbooks') + '.\n'
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result
        if validate_result["valid"]:
            self.result.output += "All content validated, ready for pack create.\n"
            self.result.status = sky_cfg.API_STATUS_SUCCESS
        else:
            self.result.status = sky_cfg.API_STATUS_FAIL
        self.result.output += validate_result["result_string"]
        if not self.args['verbose']:
            self.result.output=''
        return self.result

    def preflight_check(self):
        result = skytask.TaskResult()
        return result

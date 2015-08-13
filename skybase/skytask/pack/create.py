import logging
import os

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import pack as pack_actions
from skybase.operands import artiball as ab_object
from skybase.utils.logger import Logger


def pack_create_add_arguments(parser):

    parser.add_argument(
        '-d',
        '--directory',
        dest='base_dir',
        action='store'
    )
    parser.add_argument(
        '-b',
        '--build-id',
        dest='build_id',
        action='store',
        default=None
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
        default=False,
        help='retrieve details of artiball creation'
    )

class Create(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.WARNING)
        self.name = 'pack.create'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):
        if self.args['base_dir']:
            base_dir = self.args['base_dir']
            if base_dir.split('/')[-1] is not 'skybase':
                base_dir = os.path.join(base_dir, 'skybase')
        else:
            base_dir = os.path.join(os.getcwd(), 'skybase')

        artiball = ab_object.Artiball(base_dir)

        if self.args['build_id']:
            artiball.create_manifest_file(self.args['build_id'])
        else:
            artiball.create_manifest_file('NoBuildID')
        artiball.update_content()

        # Hardcoding default to True for pack group command, revisit later
        self.args['apply'] = True
        if self.args['apply']:
            if self.args['verbose']:
                self.logger.write('Creating package in ' + base_dir, multi_line=False)
            pack_result = pack_actions.pack(artiball.base_dir, artiball.app_source, artiball.chef_repo,
                                            artiball.chef_repo_branch, artiball.cookbooks, artiball.use_berkshelf,
                                            artiball.databags, artiball.encrypted_databags,artiball.manifest,
                                            dry_run=False, verbose=self.args['verbose'])
        else:
            if self.args['verbose']:
                self.logger.write('DRY RUN :::: Dry running steps for package creation in ' + base_dir,
                                  multi_line=False)
            pack_result = pack_actions.pack(artiball.base_dir, artiball.app_source, artiball.chef_repo,
                                            artiball.chef_repo_branch, artiball.cookbooks, artiball.use_berkshelf,
                                            artiball.databags, artiball.encrypted_databags, artiball.manifest,
                                            dry_run=True, verbose=self.args['verbose'])

        if pack_result["valid"]:
            self.result.status = sky_cfg.API_STATUS_SUCCESS
        else:
            self.result.status = sky_cfg.API_STATUS_FAIL

        self.result.output += pack_result["result_string"]
        return self.result

    def preflight_check(self):
        result = skytask.TaskResult()
        validate = skytask.get_task_class_by_name('pack.validate')(self.args)
        result = validate.execute()
        if result.status == sky_cfg.API_STATUS_FAIL:
            result.output += "Invalid content for packing, please correct accordingly.\n"
            result.status = 'FAIL'
        return result

import logging
import os

from skybase.skytask import SkyTask
from skybase.actions import sky_chef as sky_chef_actions
from skybase.utils.logger import Logger

def chef_update_cookbooks_add_arguments(parser):

    parser.add_argument(
        '-a',
        '--artiball',
        dest='artiball',
        action='store',
        default=None
    )
    parser.add_argument(
        '-p',
        '--planet',
        dest='planet',
        action='store',
        default=None
    )
    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='local',
        help='execution mode (default local)'
    )


class UpdateCookbooks(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'chef.update_cookbooks'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):
        result = 0
        artiball_data_dir = self.runner_cfg.data['artiball_data_dir']
        artiball_dir = os.path.join(artiball_data_dir, self.args['artiball'].split('.tar.gz')[0])
        if os.path.exists(artiball_dir):
            planet_data_dir = self.runner_cfg.data['planet_data_dir']
            knife_env_path = os.path.join(planet_data_dir, self.args['planet'])
            knife_config_path = os.path.join(knife_env_path, 'chef', self.args['planet'] + '.knife.rb')

            if os.path.exists(knife_config_path):
                dep_cookbook_path = os.path.join(artiball_dir, 'installation', 'chef', "cookbooks")

                cookbooks_order_file = os.path.join(artiball_dir, 'installation', 'chef', 'cookbook-order.yaml')
                with open(cookbooks_order_file) as f:
                    dependencies = f.readlines()
                    for dep in dependencies:
                        self.logger.write('Updating cookbook ' + dep.rstrip('\n') + ' in planet ' + self.args['planet'],
                                          multi_line=False)
                        self.logger.write(sky_chef_actions.cookbook_upload(knife_env_path, knife_config_path,
                                                                           dep_cookbook_path, dep.rstrip('\n'),
                                                                           self.logger),
                                          multi_line=False)
            else:
                self.logger.write("Cannot locate planet knife config " + knife_config_path
                                  + ", please confirm it exists", multi_line=False)
        else:
            self.logger.write("Cannot locate artiball " + self.args['artiball'] + ", please confirm it exists in "
                              + artiball_data_dir, multi_line=False)
            return 1
        return result

    @property
    def is_executable(self):
        if self.args['artiball'] is None:
            self.logger.write("Missing artiball argument, please use -a to specify.", multi_line=False)
            return False
        if self.args['planet'] is None:
            self.logger.write("Missing planet argument, please use -p to specify.", multi_line=False)
            return False
        return True


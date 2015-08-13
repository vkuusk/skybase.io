import logging
import os
import yaml

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import sky_chef as sky_chef_actions
from skybase.utils.logger import Logger

def chef_update_environment_add_arguments(parser):

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


class UpdateEnvironment(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'chef.update_environment'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):
        planet_data_dir = self.runner_cfg.data['planet_data_dir']
        knife_env_path = os.path.join(planet_data_dir, self.args['planet'])
        knife_config_path = os.path.join(knife_env_path, 'chef', self.args['planet'] + '.knife.rb')

        if os.path.exists(knife_config_path):
            planet_env_yaml = os.path.join(knife_env_path, self.args['planet'] + '.yaml')
            with open(planet_env_yaml, 'r') as f:
                planet_env_attr = yaml.load(f)
                chef_env_attr = planet_env_attr['services']['chefserver']['chef_environment']['default_attributes']
                chef_env_final = chef_env_attr.copy()
                chef_env_final.update(planet_env_attr)
                self.logger.write('Updating environment in planet ' + self.args['planet'], multi_line=False)
                update_environment_result = sky_chef_actions.environment_create(knife_env_path, knife_config_path,
                                                                                chef_env_final)
            f.close()
            if update_environment_result["valid"]:
                self.result.status = sky_cfg.API_STATUS_SUCCESS
            else:
                self.result.status = sky_cfg.API_STATUS_FAIL
        else:
            self.logger.write("Cannot locate planet knife config " + knife_config_path
                              + ", please confirm it exists", multi_line=False)
            self.result.status = sky_cfg.API_STATUS_FAIL

        self.result.output += update_environment_result["result_string"]
        return self.result


    def preflight_check(self):
        result = skytask.TaskResult()
        if self.args['planet'] is None:
            result.output += "Missing planet argument, please use -p to specify.\n"
            result.status = 'FAIL'
        return result



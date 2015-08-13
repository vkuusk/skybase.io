import os

from skybase import config as sky_cfg
from skybase.utils.schema import read_yaml_from_file
from skybase.service import Deploy, App, AppConfig
from skybase.service.install import ChefInstall
from skybase.schemas.artiball import ARTIBALL_SCHEMA_ARGS

class Artiball(object):

    def __init__(self, artiball_name=None, artiball_data_dir=None):
        self.artiball_name = artiball_name

        # assign skybase runner artiball data directory if not provided
        if artiball_data_dir is None:
            self.runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)
            self.artiball_data_dir = self.runner_cfg.data['artiball_data_dir']
        else:
            self.artiball_data_dir = artiball_data_dir

        self.app = App(
            self.artiball_name,
            self.artiball_data_dir,
            **ARTIBALL_SCHEMA_ARGS
        )

        self.app_config = AppConfig(
            self.artiball_name,
            self.artiball_data_dir,
            **ARTIBALL_SCHEMA_ARGS
        )

        self.deploy = Deploy.init_from_artiball(
            self.artiball_name,
            self.artiball_data_dir,
            **ARTIBALL_SCHEMA_ARGS
        )

        # TODO: new support for sensing 0,1 or many multiple installation types
        # chef install only installtion type currently supported
        self.install = ChefInstall(
            self.artiball_name,
            self.artiball_data_dir,
            **ARTIBALL_SCHEMA_ARGS
        )

    @property
    def manifest(self):
        if self.artiball_data_dir and self.artiball_name:
            # create path to manifest file
            manifest_file = os.path.join(
                self.artiball_data_dir,
                self.artiball_name,
                ARTIBALL_SCHEMA_ARGS['manifest_file'],
            )
            # return contents of manifest file if exists
            if os.path.isfile(manifest_file):
                manifest_data = read_yaml_from_file(yaml_file=manifest_file)
                if manifest_data:
                    manifest = manifest_data.get('metadata')
                    manifest['chef_cookbook_source'] = manifest_data.get('chef_cookbook_source')
                    return manifest

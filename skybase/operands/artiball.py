import logging
import os
import yaml
import sys

from skybase.utils.logger import Logger
from skybase import schemas
from pprint import pprint as pp

class Artiball(object):
    '''
    This class contains info to pack a Service into Artiball
    and perform verifications and convertions into different formats

    Mode 1: initialize blank dir so it can be checked into repo

    Mode 2: check out of repo; create a temp dir put stuff together and create tarball
            a) each


    '''

    def __init__(self, base_dir=None):
        logging.basicConfig(level=logging.INFO)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)

        self.base_dir = base_dir
        self.yaml_files = []

        self.app_source = None
        self.cookbooks = []
        self.chef_repo = None
        self.chef_repo_branch = None
        self.use_berkshelf = False
        self.databags = []
        self.encrypted_databags = []

        self.manifest = {}

        self.initialize()

    def initialize(self):
        if not self.base_dir:
            self.base_dir = os.path.join(os.getcwd(), 'skybase')
        elif self.base_dir.split('/')[-1] != 'skybase':
            self.base_dir = os.path.join(self.base_dir, 'skybase')
        self.load_yaml_files()
        return self.base_dir

    def load_yaml_files(self):
        for path, dirs, files in os.walk(self.base_dir):
            for file in files:
                if file.split('.')[-1] == 'yaml':
                    self.yaml_files.append(os.path.join(path, file))

    def update_content(self):
        config_file = os.path.join(self.base_dir, 'skybase.yaml')
        with open(config_file, 'r') as temp_file:
            config = yaml.load(temp_file)
            self.app_source = config['packing']['application']['source_location']
            installations = config['packing']['installations']
            for installation in installations:
                if installation.get("chef"):
                    self.databags = installation['chef']['databags']
                    self.encrypted_databags = installation['chef']['encrypted_databags']

                    self.chef_repo = installation['chef']['repository_url']
                    self.chef_repo_branch = installation['chef']['repository_branch']
                    self.use_berkshelf = installation['chef']['cookbooks']['dependencies_from_berkshelf']
        temp_file.close()

        deployment_file = os.path.join(self.base_dir, 'deployment', 'main_deployment.yaml')
        with open(deployment_file, 'r') as temp_file:
            try:
                deployment = yaml.load(temp_file)
            except yaml.scanner.ScannerError:
                self.logger.write("Invalid yaml syntax  " + deployment_file + '\n', multi_line=True)
                sys.exit(1)
            stacks = deployment['stacks']
            for stack in stacks:
                roles = stack['roles']
                for role in roles:
                    for runlist_item in role['chef_role_runlist']:
                        self.cookbooks.append(runlist_item.split('::')[0])
        self.cookbooks = sorted(set(self.cookbooks))
        temp_file.close()

    def update_manifest(self, build_id=None):
        self.manifest = schemas.create_unordered_dict_from_schema(
            schemas.get_schema('manifest_yaml_schema', 'artiball'), 'manifest', 'artiball')
        if build_id:
            self.manifest['metadata']['build_id'] = build_id
        for file in self.yaml_files:
            if 'main_deployment' in file:
                with open(file, 'r') as temp_file:
                    try:
                        deployment_data = yaml.load(temp_file)
                    except yaml.scanner.ScannerError:
                        self.logger.write("Invalid yaml syntax  " + file + '\n', multi_line=True)
                        sys.exit(1)
                    schemas.set_indicators()
                    if deployment_data['definition']['service_name'] not in schemas.INDICATORS:
                        self.manifest['metadata']['app_name'] = deployment_data['definition']['service_name']
                    if deployment_data['definition']['version'] not in schemas.INDICATORS:
                        self.manifest['metadata']['app_version'] = deployment_data['definition']['version']
                    if deployment_data['definition']['chef_type'] == 'server':
                        with open(os.path.join(self.base_dir, 'skybase.yaml'), 'r') as config_file:
                            try:
                                skybase_data = yaml.load(config_file)
                            except yaml.scanner.ScannerError:
                                self.logger.write("Invalid yaml syntax  " + file + '\n', multi_line=True)
                                sys.exit(1)
                            schemas.set_indicators()
                            for installation in skybase_data['packing']['installations']:
                                if installation.get("chef"):
                                    if (installation['chef']['repository_url'] not in schemas.INDICATORS) and \
                                            (installation['chef']['repository_branch'] not in schemas.INDICATORS):
                                        self.manifest['chef_cookbook_source'] = installation['chef']['repository_url'] + \
                                                                                '=' + installation['chef']['repository_branch']
                        config_file.close()
                temp_file.close()

    def create_manifest_file(self, build_id=None):
        self.update_manifest(build_id)
        manifest_file = os.path.join(self.base_dir, 'manifest.yaml')
        if os.path.exists(manifest_file):
            os.remove(manifest_file)
        with open(manifest_file, 'wb') as temp_file:
            yaml.dump(self.manifest, temp_file, allow_unicode=True, default_flow_style=False)
        temp_file.close()
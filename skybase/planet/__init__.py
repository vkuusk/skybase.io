import os
import json


from skybase import config as sky_cfg
from skybase.utils.schema import read_yaml_from_file


class Planet(object):

    # TODO: provide @classmethod init_from_name() which concatenates planet name with default dir or otherwise provided planet data path
    def __init__(self, planet_name=None, planet_data_dir=None):

        self.planet_name = planet_name

        # assign path to planet data directory
        if planet_data_dir is None:
            # retrieve path to planet from runner configuration
            self.runner_cfg = sky_cfg.SkyConfig.init_from_file(
                'runner',
                config_dir=sky_cfg.CONFIG_DIR
            )
            self.planet_data_dir = self.runner_cfg.data['planet_data_dir']
        else:
            self.planet_data_dir = planet_data_dir

        # Initialize these variables
        self.definition = None
        self.services = None
        self.resource_ids = None
        self.planet = None
        self.universe = None
        self.orchestration_engine = None
        self.accountprofile = None
        self.provider = None
        self.region = None

        # TODO: provide @classmethod init_from_file() which takes planet.yaml filename
        if self.planet_name:
            self._yaml_data = self._load_yaml_data()

            # required planet yaml main sections
            self.definition = self._yaml_data['definition']
            self.services = self._yaml_data['services']
            self.resource_ids = self._yaml_data.get('resource_ids')

            # map other key attributes required by skybase and jinja
            self.planet = self.definition['planet']
            self.universe = self.definition['universe']
            self.orchestration_engine = self.definition['orchestration_engine']
            self.accountprofile = self.definition['accountprofile']
            self.provider = self.definition['provider']
            self.region = self.definition['region']
            self.resource_ids['subnets_by_type'] = self.get_subnets_by_type()

    # TODO: raise error if planet yaml file not found
    # prepare absolute filename pointing to planet yaml file
    def get_yaml_filename(self):
        return '/'.join(
            [
                self.planet_data_dir,
                self.planet_name,
                self.planet_name + '.yaml'
            ]
        )

    def _load_yaml_data(self):
        return read_yaml_from_file(yaml_file=self.get_yaml_filename())

    # TODO: YAML validation for all required entries
    def validate_yaml_data(self):
        pass

    # TODO: raise error if knife.rb file not found
    def get_knife_file(self):
        if self.services:
            knife_file = self.services.get('chefserver', {}).get('knife_rb_name')
            if knife_file:
                return os.path.join(self.planet_data_dir, self.planet, 'chef', knife_file)

    def get_chef_knife_attributes(self):
        attribs = {}
        if not self.services:
            return attribs

        attribs['CHEF_CREDS_PATH'] = os.path.join(self.runner_cfg.data['runner_credentials_dir'], 'chef', self.planet_name)
        attribs['CHEF_NODE_NAME'] = self.services.get('chefserver', {}).get('user_name')
        attribs['CHEF_CLIENT_KEY'] = self.services.get('chefserver', {}).get('client_key')
        attribs['CHEF_VALIDATION_KEY'] = self.services.get('chefserver', {}).get('validation_key')
        attribs['CHEF_SERVER_URL'] = self.services.get('chefserver', {}).get('chef_server_url')
        attribs['CHEF_VALIDATION_CLIENT_NAME'] = self.services.get('chefserver', {}).get('validation_client_name')

        return attribs

    def get_yumrepo_bucket(self):
        if self.services:
            return self.services.get('yumrepo', {}).get('bucket')

    def get_planet_repo_path(self):
        planet_data = self.planet_data_dir
        if planet_data:
            return os.path.join(planet_data, self.planet)

    def get_prov_object_store_base_path(self):
        prov_object_store_path = (
            self.services['prov-object-store']['scheme'] + '/'.join(
                [
                    self.services['prov-object-store']['bucket'],
                    self.services['prov-object-store']['url']
                ]
            )
        )
        return prov_object_store_path

    # vpc_id only available after planet state has been created
    @property
    def vpc_id(self):
        if self.resource_ids:
            return self.resource_ids.get('vpc_id')

    # subnet only available after planet state has been created
    @property
    def subnet(self):
        if self.resource_ids:
            return self.resource_ids.get('subnet')

    # list all services
    @property
    def list_all_services(self):
        if self.services:
            return self.services.keys()

    @property
    def planet_as_dict(self):
        return {
            'definition': self.definition,
            'services': self.services,
            'resource_ids': self.resource_ids
        }

    @property
    def chef_env_attr(self):
        return {
            "json_class": "Chef::Environment",
            "chef_type": "environment",
            "name": self.services['chefserver']['chef_environment']['name'],
            "description": self.services['chefserver']['chef_environment']['description'],
            "default_attributes": self.services['chefserver']['chef_environment']['default_attributes'],
            "override_attributes": {},
            "cookbook_versions": {}
        }

    def get_subnets_by_type(self):
        '''
        create data structure of subnets with type as key and ids as list.
        return list of ids as json for consumption in jinja templates
        '''
        subnets = {}
        for sub_id, sub_val in self.subnet.items():
            sub_type = sub_val['type']
            if sub_type not in subnets:
                subnets[sub_type] = []
            subnets[sub_type].append(sub_val['id'])
        subnets_as_json = {k: json.dumps(v) for k, v in subnets.items()}
        return subnets_as_json

    def __repr__(self):
        return str('Planet %s:' % self.planet) + str(self.__dict__)

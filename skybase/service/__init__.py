from .deploy import Deploy
from .app import App
from .app_config import AppConfig
from .install import Install

from skybase import __version__
from skybase.utils import basic_timestamp, merge_list_of_dicts, schema

class SkyService(object):
    def __init__(self,
                 name=None,
                 app=App(),
                 app_config=AppConfig(),
                 install=Install(),
                 deploy=Deploy(),
                 manifest=None):
        self.name = name
        self.app= app
        self.app_config = app_config
        self.install = install
        self.deploy = deploy
        self.manifest = manifest

    @classmethod
    def init_from_artiball(cls, artiball_name, artiball_data_dir=None):
        from skybase.artiball import Artiball
        artiball = Artiball(artiball_name, artiball_data_dir)
        return cls(artiball.artiball_name,
                   artiball.app,
                   artiball.app_config,
                   artiball.install,
                   artiball.deploy,
                   artiball.manifest)


    @property
    def metadata(self):
        metadata = self.manifest if self.manifest else dict()
        metadata.update({'source_artiball': self.name})
        return metadata

    @property
    def registration(self):
        registration = {
            'blueprint': self.deploy.blueprint,
            'metadata': self.metadata,
        }
        return registration

    # TODO: this can be moved to install if enc db secret *only* param
    def get_template_params(self):
        parameters = []
        if self.install.encrypted_databags:
            parameters.append(self.install.get_template_params())
        return parameters


    def get_role_attributes(self, stack_name, role_name, chef_role_name, universe, planet_name):

        # main app config as dictionary is basis for acquiring role attribtes
        app_config = self.app_config.app_config

        # clear list of attributes dictionaries for each role created
        attr_list = []
        service_common = app_config.get('common') if app_config is not None else {}
        if service_common is not None:
            attr_list.append(service_common)

        # initialize with service level attributes
        try:
            stacks = app_config.get('stacks', {}).get(stack_name, {}) if app_config is not None else {}
            attr_list.append({k:v for k, v in stacks.items() if k != 'roles'})
        except Exception as e:
            stacks = {}

        # include role level attributes
        try:
            role = stacks.get('roles', {}).get(role_name, {})
            attr_list.append({k:v for k, v in role.items() if k != 'universes'})
        except Exception as e:
            role = {}

        # include universe level attributes
        try:
            universe = role.get('universes', {}).get(universe, {})
            attr_list.append({k:v for k, v in universe.items() if k != 'planets'})
        except Exception as e:
            universe = {}

        # include planet level attributes (dev, qa, &c.)
        try:
            planet = universe.get('planets', {}).get(planet_name, {})
            attr_list.append({k:v for k, v in planet.items()})

            # HACK to merge the dictionary instead of overwriting
            merged_dict = {}
            for i in attr_list:
                merged_dict = schema.rec_dict_merge(merged_dict, i)
            # overwrite by merged
            attr_list.append(merged_dict)
        except Exception as e:
            pass

        # acquire role run list (as list) from artiball stack roles
        stack_role_config = self.deploy.get_stack_role_config_by_name(stack_name, role_name)
        chef_role_runlist = stack_role_config['chef_role_runlist']

        # format run list per chef's specifications
        run_list = ['recipe[' + recipe + ']' for recipe in chef_role_runlist]

        # prepare keyword args role creation
        chef_role_attr = {
            "name": chef_role_name,
            "description": chef_role_name + " description",
            "json_class": "Chef::Role",
            "default_attributes": merge_list_of_dicts(attr_list),
            "override_attributes": {},
            "chef_type": "role",
            "run_list" : run_list,
            "env_run_lists": {}
        }

        return chef_role_attr


class SkyRuntime(object):
    '''
    namespace for runtime arguments used by template rendering and workflows
    list of Key=Value attributes
    '''

    def __init__(self, tag=None, apply=False, **kwargs):
        self.tag = tag
        self.apply = apply
        self.set_attrs(**kwargs)

    def set_attrs(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(''.join([self.__class__.__name__, '(', str(self.__dict__), ')']))


class SkySystem(object):
    def __init__(self, version=__version__, timestamp=basic_timestamp(), **kwargs):
        self.version = version
        self.timestamp = timestamp
        self.set_attrs(**kwargs)

    def set_attrs(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(''.join([self.__class__.__name__, '(', str(self.__dict__), ')']))

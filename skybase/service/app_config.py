import os

from skybase.utils.schema import read_yaml_from_file, convert_stack_roles_to_dict

class AppConfig(object):
    def __init__(self, service_name=None, service_dir=None, **kwargs):
        self.service_name = service_name
        self.service_dir = service_dir
        self.config_dir = kwargs.get('config_dir')
        self.config_file = kwargs.get('config_file')

    @property
    def app_config(self):
        filename = os.path.join(self.get_appconfig_path(), self.config_file)
        if os.path.isfile(filename):
            app_config = read_yaml_from_file(filename)
            # TODO: decision ==> stacks converted at instantiation or on-demand
            stacks = convert_stack_roles_to_dict(app_config.get('stacks'))
            app_config['stacks'] = stacks
            return app_config

    def get_appconfig_path(self):
        return os.path.join(self.service_dir, self.service_name, self.config_dir)

    def __repr__(self):
        return str(''.join([self.__class__.__name__, '(', str(self.__dict__), ')']))
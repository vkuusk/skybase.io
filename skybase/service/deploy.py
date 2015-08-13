import os

from skybase.utils.schema import read_yaml_from_file
from skybase.utils.schema import convert_stack_roles_to_dict


class Deploy(object):
    def __init__(self, service_name=None, service_dir=None, definition=None, stacks=None):
        self.service_name = service_name
        self.service_dir = service_dir
        self.definition = definition
        self.stacks = stacks

        # runtime attributes defined by external processes, commands, &c.
        self.stack_launch_list = None

    @classmethod
    def init_from_artiball(cls, service_name, service_dir, **kwargs):
        def get_service_yaml_filename():
            yf = os.path.join(
                service_dir,
                service_name,
                kwargs.get('deploy_dir'),
                kwargs.get('deploy_file'),
            )
            return yf
        return Deploy.init_from_file(service_name, service_dir, get_service_yaml_filename())

    @classmethod
    def init_from_file(cls, service_name, service_dir, filename):
        # initialize return vars
        definition = stacks = None

        # read service from deployment yaml file
        main_deployment = read_yaml_from_file(filename)

        # TODO: decision ==> stacks converted at instantiation or on-demand
        # extract service attributes
        if main_deployment:
            definition = main_deployment.get('definition')
            stacks = convert_stack_roles_to_dict(main_deployment.get('stacks'))

        return cls(service_name, service_dir, definition, stacks)

    # TODO: deprecate property and substitute with stacks.keys() in skycloud.stack_launch_list()
    @property
    def stack_ids(self):
        return self.stacks.keys() if self.stacks else []

    @property
    def blueprint(self):
        return {
            'definition': self.definition,
            'stacks': self.stacks,
        }

    def get_stack_attr_by_name(self, stackname):
        return self.stacks[stackname]

    def get_stack_roles(self, stackname):
        return self.stacks[stackname]['roles']

    def get_stack_role_config_by_name(self, stackname, rolename):
        return self.get_stack_attr_by_name(stackname)['roles'][rolename]

    def get_service_stack_roles(self):
        role_instance_components = []

        for stack, values in self.stacks.items():
            for role in values['roles']:
                role_instance_components.append(
                    (self.service_name, stack, role))

        return role_instance_components

    def __repr__(self):
        return str(''.join([self.__class__.__name__, '(', str(self.__dict__), ')']))
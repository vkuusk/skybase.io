import os
import tempfile
import jinja2

from skybase import config as sky_cfg
from skybase.utils import make_temp_directory, basic_timestamp
from skybase.schemas.artiball import ARTIBALL_SCHEMA_ARGS

from . import aws, openstack

def render_template(source_template=None, searchpath=None, **kwargs):
    template_loader = jinja2.FileSystemLoader(searchpath=searchpath)
    template_env = jinja2.Environment(loader=template_loader, extensions=['jinja2.ext.do'])

    # extend default environment with timestamp function
    template_env.globals['timestamp'] = basic_timestamp

    template = template_env.get_template(source_template)
    return template.render(**kwargs)

def preprocess_userdata(template):
    # apply transformations to userdata template and return as list of lines
    userdata_as_list = []
    for line in template.split('\n'):
        userdata_as_list.append(r'"{0}",'.format(line))
    return userdata_as_list

class CloudTemplate(object):

    SKYBASE_CLOUD_TEMPLATE_DEFAULT = 'std-chef-client/std-chef-client'

    '''
    representation of a single cloud provider template
    '''
    def __init__(self, planet, service, runtime, system, stackname, **kwargs):
        self.planet = planet
        self.service = service
        self.runtime = runtime
        self.system = system
        self.stackname = stackname
        self.stack_launch_name = kwargs.get('stack_launch_name', self.stackname)
        self.runner_cfg = kwargs.get('runner_cfg', sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR))

        # derived temmplate attributes
        self._stackattr = self.service.deploy.get_stack_attr_by_name(self.stackname)
        self.stacktype = self._stackattr.get('type')
        self.template_name = self.get_template_name()

    @property
    def template_body(self):
        return self._render()


    def get_template_name(self):
        cloud_template_name = self._stackattr.get('cloud_template_name')

        if cloud_template_name is None and self.stacktype == 'standard':
            cloud_template_name = CloudTemplate.SKYBASE_CLOUD_TEMPLATE_DEFAULT

        return cloud_template_name


    def get_template_searchpath(self, extrapath=None):
        # compose jinja template search path from standard templates directory,
        # service and any extra path elements submitted
        searchpath = [self.runner_cfg.data['std_templates_dir'],
                      os.path.join(self.service.deploy.service_dir,
                                   self.service.deploy.service_name,
                                   ARTIBALL_SCHEMA_ARGS['deploy_dir'])]
        if extrapath:
            searchpath.append(extrapath)

        return searchpath

    def get_core_template_args(self):
        service_template_args = {
            'service_name': self.service.manifest['app_name'],
            'definition': self.service.deploy.definition,
            'stacks': self.service.deploy.stacks,
        }

        # prepare arguments for cloud template
        core_template_args = {
            'planet': self.planet.planet_as_dict,
            'service': service_template_args,
            'runtime': self.runtime,
            'system': self.system,
            'stack_id': self.stackname,
            'stackname': self.stack_launch_name,
        }
        return core_template_args

    def _render(self):

        '''
        create a temporary work directory for creating and caching dynmaically
        generated userdata templates. temp directory and its contents are
        deleted automatically by context manager after cloud template is returned
        '''
        with make_temp_directory() as temp_work_dir:

            # prepare arguments for cloud template
            cloud_template_args = self.get_core_template_args()
            cloud_template_args.update({'user_data': self._preprocess_user_data(temp_work_dir)})

            # render primary template, extending searchpath to temporary dir
            # holding role-based userdata jinja templates
            cloud_template = render_template(
                searchpath=self.get_template_searchpath(extrapath=temp_work_dir),
                source_template=self._get_template_filename(self.template_name, 'jinja2'),
                **cloud_template_args)

            return cloud_template


    def _get_userdata_role_template_names(self):

        userdata_template_name_by_role = {}

        for role, attr in self._stackattr['roles'].items():
            userdata_template_name_by_role[role] = attr.get('userdata_template_name')
            if userdata_template_name_by_role[role] is None and self.stacktype == 'standard':
                userdata_template_name_by_role[role] = self.get_template_name()

        return userdata_template_name_by_role


    def _get_template_filename(self, template_name, file_ext):
        return '.'.join([template_name, self.planet.orchestration_engine, file_ext])


    def _preprocess_user_data(self, temp_work_dir):

        # initialize results object
        user_data = {}

        # prepare arguments passed to rendering engine
        user_data_args = self.get_core_template_args()


        # create a role specific userdata template
        for role, userdata_template in self._get_userdata_role_template_names().items():

            # include role-based attributes for inclusion if exists
            user_data_args['role'] = self._stackattr['roles'][role]

            # render userdata template
            user_data_role_template = render_template(
                searchpath=self.get_template_searchpath(),
                source_template=self._get_template_filename(userdata_template, 'userdata.jinja2'),
                **user_data_args)

            # final processing of the dynamically rendered userdata template
            # handed off to orchestration engine specific module/function
            user_data_by_role = []
            if self.planet.orchestration_engine == 'cfn':
                user_data_by_role = preprocess_userdata(user_data_role_template)
            elif self.planet.orchestration_engine == 'heat':
                user_data_by_role = preprocess_userdata(user_data_role_template)

            # create template tempfile in work directory
            fd, ud_tempfile = tempfile.mkstemp(prefix=temp_work_dir + os.path.sep, suffix='.jinja2')

            # write preprocessed and rendered userdata to tempfile
            with open(ud_tempfile, 'w') as f:
                [f.write(line + '\n') for line in user_data_by_role]

            # save list of userdata tempfile names
            user_data[role] = ud_tempfile.split(os.sep)[-1]

        return user_data

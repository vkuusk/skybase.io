import os
import json

from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import render as r_acts
from skybase.utils.logger import Logger

from skybase import exceptions as err


def render_full_standard_add_arguments(parser):

    parser.add_argument(
        '-t', '--template',
        dest='template_file_name',
        action='store',
        default=None,
        help='Jinja template file to render (required).'
    )

    parser.add_argument(
        '-u', '--userdata',
        dest='userdata_files',
        action='append',
        help='Jinja templates of Shell scripts to be + inserted into main template. Can be used '
    )

    parser.add_argument(
        '-p', '--planet',
        dest='planet',
        action='store',
        default=None,
        help='Name of the planet from a standard Skybase planet repository'
    )

    parser.add_argument(
        '-f', '--file',
        dest='data_files',
        action='append',
        help='Yaml data files in form NS=filename.yml  NS = NameSpace to use in the jinja template'
    )

    parser.add_argument(
        '-r', '--runtime',
        dest='runtime_keys',
        action='append',
        help='list of <KeyName=Value> to use in the jinja templates'
    )

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='local',
        help='execution mode (default LOCAL)'
    )


class FullStandard(SkyTask):
    def __init__(self, all_args, runner_cfg):
        SkyTask.__init__(self, all_args, runner_cfg)

        #self.logger = Logger(logging.getLogger(__name__), logging.INFO)

        self.name = 'render.full_standard'
        self.args = all_args
        self.runner_cfg = runner_cfg



    def execute(self):

        result = dict()

        if self.args['apply']:
            run_mode = 'apply'
        else:
            run_mode = 'dry_run'

        # ----------------------------------
        # get needed values from the config


        template_file = os.path.expanduser(self.args['template_file_name'])

        user_data_files = self.args['userdata_files']

        render_space_files = []
        if self.args['data_files'] is not None:
            for dict_name in self.args['data_files']:
                ns = dict()
                (d, f) = dict_name.split('=')
                ns['ns'] = d
                ns['filename'] = os.path.expanduser(f)
                if not os.path.exists(ns['filename']):
                    raise err.SkyBaseError('NOT FOUND: ' + ns['filename'])
                render_space_files.append(ns)

        # add planet yaml to the render space files:
        if self.args['planet'] is not None:
            planet_name = self.args['planet']
            planet_data_dir = self.runner_cfg.data['planet_data_dir']
            ns = dict()
            ns['ns'] = 'planet'
            ns['filename'] = os.path.join(planet_data_dir, planet_name, planet_name + '.yaml')
            if not os.path.exists(ns['filename']):
                    raise err.SkyBaseError('NOT FOUND: ' + ns['filename'])
            render_space_files.append(ns)

        key_value_dict = dict()
        if self.args['runtime_keys'] is not None:
            for item in self.args['runtime_keys']:
                [k, v] = item.split('=')
                key_value_dict[k] = v

        #
        rendered = r_acts.sky_full_rendering(template_file, user_data_files, render_space_files, key_value_dict)

        result['data'] = rendered
        result['type'] = skytask.output_format_raw

        return result

    def preflight_check(self):

        self.preflight_check_result['status'] = 'pass'



        return self.preflight_check_result

    @property
    def is_executable(self):

        error_message = ''

        if not self.args['template_file_name']:
            error_message = 'missing template filename argument. use: -t <template_file>'

        result = {'status': 'fail', 'message': ''}

        if len(error_message) == 0:
            result['status'] = 'pass'
        else:
            result['message'] = error_message

        return result
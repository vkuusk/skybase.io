import os

from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import render as r_acts
from skybase.utils.logger import Logger




def render_single_template_add_arguments(parser):

    parser.add_argument(
        '-t', '--template',
        dest='template_file_name',
        action='store',
        help='Jinja template file to render (required).'
    )

    parser.add_argument(
        '-f', '--file',
        dest='data_files',
        action='append',
        help='Yaml data files in form NS=filename.yml  NS = NameSpace to use in the jinja template'
    )

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='local',
        help='execution mode (default LOCAL)'
    )


class SingleTemplate(SkyTask):
    def __init__(self, all_args, runner_cfg):
        SkyTask.__init__(self, all_args, runner_cfg)

        #self.logger = Logger(logging.getLogger(__name__), logging.INFO)

        self.name = 'render.single_template'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):

        result = dict()

        if self.args['apply']:
            run_mode = 'apply'
        else:
            run_mode = 'dry_run'

        #self.logger.write('Executing "' + self.name + '" command in MODE: ' + run_mode)

        template_file = os.path.expanduser(self.args['template_file_name'])

        name_spaces = []
        for dict_name in self.args['data_files']:
            ns = dict()
            (d, f) = dict_name.split('=')
            ns['ns'] = d
            ns['filename'] = os.path.expanduser(f)
            name_spaces.append(ns)

        rendered = r_acts.single_template_render(template_file, name_spaces)

        # TODO: define the standard data structure for the Task result dictionary
        #
        result['data'] = rendered.body
        result['type'] = skytask.result_type_jsonstr

        return result

    @property
    def is_executable(self):

        criteria_met = True

        # test different things:
        if not self.args['template_file_name']:
            criteria_met = False



        if criteria_met:
            result = True
        else:
            result = False

        return result

'''
sample use for the testing:
render single-template:

./scripts/sky render single-template -t ~/skybase-testing-temp/my-template.jinja \
                                    -f dict1=~/skybase-testing-temp/file1.yaml \
                                    -f dict2=~/skybase-testing-temp/file2.yaml \
                                    -c ~/skybase-testing-temp/

'''
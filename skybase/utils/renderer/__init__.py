

import jinja2

from skybase.utils import schema


class JinjaRenderer(object):
    '''

    standalone rednderer accepts arguments in form
    > render -t CFN.json.jinja2 -f KeyNameA=FileNameA.yaml [ -f KeyNameB=FilenameB.yaml ....] [-p PlanetName]
    and renders jinja template using all yaml files
    data from yaml files are referenced indside jinja template by the namespace, which is a "KeyName"
    e.g. KeyNameA.root.internal_key1

    '''

    def __init__(self, template_string, **kwargs):
        '''

        :param template_string:
        :param kwargs: These are dictionaries which will be used as namespaces for rendering
        :return:
        '''

        env = jinja2.Environment()

        template = env.from_string(template_string)

        self.body = template.render(**kwargs)

    @classmethod
    def render_string_template_from_files(cls, template_file, data_files):
        '''
        Data_Files is a list of dictionaries {'ns': 'namespacename','filename': 'SomeFileName'}
        :param template_file:
        :param data_files:
        :return:
        '''

        with open(template_file, 'r') as tf:
            template_string = tf.read()

        data_dict = {}
        for df in data_files:
                data_dict[df['ns']] = schema.read_yaml_from_file(df['filename'])

        rendered = cls(template_string, **data_dict)

        return rendered

    @classmethod
    def render_filesystem_template(cls, source_template=None, searchpath=None, **kwargs):
        template_loader = jinja2.FileSystemLoader(searchpath=searchpath)
        template_env = jinja2.Environment(loader=template_loader)

        # extend default environment with timestamp function
        template_env.globals['timestamp'] = basic_timestamp

        template = template_env.get_template(source_template)
        return template.render(**kwargs)

# ============================================================
#    TEST/USAGE example
# ============================================================
# from skybase.utils.renderer import JinjaRenderer as sky_renderer
#
#
#
# my_string = '''
# 1
# {{ name.kuku }}
# 2
# 3
# 4
# '''
#
# myargs = {'name': {'kuku': 'TestingName-From-KWARGS'}}
#
# template = sky_renderer(my_string, **myargs )
#
# print template.body
#
# jinja_file = './data/renderer/test.jinja2'
#
# data_spaces = [
#     {
#         'ns': 'name',
#         'filename': './data/renderer/test.yaml'
#     }
# ]
#
# newtemplate = sky_renderer.render_string_template_from_files(jinja_file, data_spaces)
#
# print '\n', newtemplate.body
# ============================================================
#    END of TEST/USAGE example
# ============================================================
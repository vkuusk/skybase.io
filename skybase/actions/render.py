
from skybase.utils.renderer import JinjaRenderer
from skybase.utils import schema

# Actions for the RENDER group of commands
def single_template_render(template_file, name_spaces):
    '''
    :param template_file: full path to the template file

    :param name_spaces: dictionary of many  { 'ns': namespace, 'filename': full_path_to_a_yaml_file}

    :return: string rendered using all yaml files
    '''
    # For now it's a simple


    rendered = JinjaRenderer.render_string_template_from_files(template_file, name_spaces)

    return rendered

def sky_full_rendering(template_file, user_data_files, render_space_files, key_value_dict):
    '''

    :param template_file: main Jinja template
    :param user_data_files: Jinja templates to be included into main Jinja Template
    :param name_space_files: list of yaml data file to be used for rendering dict {'names_space': 'filename'}
    :param key_value_list: List of [ 'keyname'='keyvalue' ] which is converted to dict and keynames are available
    for rendering
    :return:
    '''

    result = ''


    # main template
    source_template = template_file

    # process userdata templates so they can be inserted into the main template
    # for each file do jinja rendering
    for f in user_data_files:
        pass



    # first assemble dictionary of dict to user for rendering:
    data_dict = dict()
    for df in render_space_files:
        data_dict[df['ns']] = schema.read_yaml_from_file(df['filename'])

    data_dict.update(key_value_dict)


    with open(template_file, 'r') as tf:
            template_string = tf.read()

    rendered_template = JinjaRenderer(template_string, **data_dict)


    result = rendered_template.body


    return result
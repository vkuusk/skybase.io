import os
import ntpath
import yaml

from distutils import dir_util
from distutils import file_util

from skybase.utils import schema as schema_util


def set_indicators():
    global BOOL_TYPE_INDICATOR
    BOOL_TYPE_INDICATOR = "CHANGE_ME[BOOL]"
    global INT_TYPE_INDICATOR
    INT_TYPE_INDICATOR = "CHANGE_ME[INT]"
    global STR_TYPE_INDICATOR
    STR_TYPE_INDICATOR= "CHANGE_ME[STRING]"
    global STR_TYPE_OPTIONAL_INDICATOR
    STR_TYPE_OPTIONAL_INDICATOR= "CHANGE_OR_REMOVE_ME[STRING]"
    global LIST_TYPE_INDICATOR
    LIST_TYPE_INDICATOR = ["CHANGE_OR_REMOVE_ME[LIST_ITEM]", "CHANGE_OR_REMOVE_ME[LIST_ITEM]"]
    global DICT_KEY_TYPE_INDICATOR
    DICT_KEY_TYPE_INDICATOR = "CHANGE_OR_REMOVE_ME[DICT_ITEM_KEY]"
    global DICT_VALUE_TYPE_INDICATOR
    DICT_VALUE_TYPE_INDICATOR = "CHANGE_OR_REMOVE_ME[DICT_ITEM_VALUE]"

    global INDICATORS
    INDICATORS = [BOOL_TYPE_INDICATOR, INT_TYPE_INDICATOR, INT_TYPE_INDICATOR,
              STR_TYPE_INDICATOR, STR_TYPE_OPTIONAL_INDICATOR,
              DICT_KEY_TYPE_INDICATOR, DICT_VALUE_TYPE_INDICATOR]

    global REQUIRED_INDICATORS
    REQUIRED_INDICATORS = [BOOL_TYPE_INDICATOR, INT_TYPE_INDICATOR, INT_TYPE_INDICATOR,
              STR_TYPE_INDICATOR, DICT_KEY_TYPE_INDICATOR, DICT_VALUE_TYPE_INDICATOR]

    global LIST_TYPE
    LIST_TYPE = "LIST"


def get_schema(schema_name, operand):
    imported = getattr(__import__("skybase.schemas", fromlist=[operand]), operand)
    if hasattr(imported, schema_name):
        return getattr(imported, schema_name)
    return []


def get_file_schema_name(filename):
    filename = os.path.basename(filename)
    return filename.replace('.', '_') + '_schema'


def create_dir_tree_from_schema(base_dir, operand, dry_run=False, force=False):
    result_string = ""
    for entry in get_schema(operand + "_schema", operand):
        dir_path = os.path.join(base_dir, "/".join(entry[0]))

        # create directories
        if not os.path.exists(dir_path):
            if dry_run:
                result_string += "Directory " + dir_path + " would be created.\n"
            else:
                result_string += "Creating directory " + dir_path + "\n"
            dir_util.mkpath(dir_path, dry_run=dry_run)

        # if a file is defined, create file
        for file in entry[1]:
            schema_attr = get_file_schema_name(file)
            file_schema = get_schema(schema_attr, operand)
            if file_schema:
                result_string += create_yaml_from_schema(os.path.join(dir_path, file), file_schema, operand,
                                                         dry_run=dry_run, force=force)
            else:
                if dry_run:
                    result_string += "File " + os.path.join(dir_path, file) + " would be created:\n"
                    result_string += "#Blank " + file + " created by skybase\n"
                else:
                    result_string += "Creating file " + os.path.join(dir_path, file) + "\n"
                    file_util.write_file(os.path.join(dir_path, file), "#Blank " + file + " created by skybase")
    return result_string


def create_yaml_from_schema(path, file_schema, operand, dry_run=False, force=False):
    result_string = ""
    content_index = 0
    if isinstance(file_schema[0], basestring):
        header = file_schema[0]
        content_index = 1
    content = file_schema[content_index:]
    content_dict = create_dict_from_schema(content, os.path.basename(path).split('.')[0], operand)

    noalias_dumper = yaml.dumper.SafeDumper
    noalias_dumper.ignore_aliases = lambda self, data: True
    noalias_dumper.add_representer(schema_util.UnsortableOrderedDict, yaml.representer.SafeRepresenter.represent_dict)

    if dry_run:
        result_string += "File " + path + " would be created:\n"
        result_string += header + "\n"
        result_string += yaml.dump(content_dict, allow_unicode=True, default_flow_style=False, Dumper=noalias_dumper)
    elif (not force) and os.path.exists(path):
        result_string += "File " + path + " exists, use --force to override.\n"
    else:
        result_string += "Creating file " + path + "\n"
        file_util.write_file(path, header + '\n')
        with open(path, 'w') as temp_file:
            yaml.dump(content_dict, temp_file, allow_unicode=True, default_flow_style=False, Dumper=noalias_dumper)
        temp_file.close()
    return result_string


def create_dict_from_schema(content_schema, schema_attr_prefix, operand):
    dict = schema_util.UnsortableOrderedDict()
    for line in content_schema:
        key = line[0]
        val = line[1]

        if val and (val[0] == LIST_TYPE):
            schema_attr_prefix = schema_attr_prefix + '_' + key[-1]
            sub_schema_attr = schema_attr_prefix + '_yaml_schema'
            sub_dict = create_dict_from_schema(get_schema(sub_schema_attr, operand), schema_attr_prefix, operand)
            list = []
            list.append(sub_dict)
            line_dict = schema_util.rec_ordered_dict_from_list(key, list, True)
        else:
            line_dict = schema_util.rec_ordered_dict_from_list(key, val, False)

        dict = schema_util.rec_ordered_dict_merge(dict, line_dict)
    return dict


def create_unordered_dict_from_schema(content_schema, schema_attr_prefix, operand):
    dict = {}
    for line in content_schema:
        key = line[0]
        val = line[1]

        if val and (val[0] == LIST_TYPE):
            schema_attr_prefix = schema_attr_prefix + '_' + key[-1]
            sub_schema_attr = schema_attr_prefix + '_yaml_schema'
            sub_dict = create_dict_from_schema(get_schema(sub_schema_attr, operand), schema_attr_prefix, operand)
            list = []
            list.append(sub_dict)
            line_dict = schema_util.rec_dict_from_list(key, list, True)
        else:
            line_dict = schema_util.rec_dict_from_list(key, val, False)

        dict = schema_util.rec_dict_merge(dict, line_dict)
    return dict


def get_missing_paths_from_schema(base_dir, operand):
    dir_dict = {}
    root_dir = base_dir.rstrip(os.sep)
    start = root_dir.rfind(os.sep) + 1
    for path, dirs, files in os.walk(root_dir):
        folders = path[start:].split(os.sep)
        subdir = dict.fromkeys(files, True)
        parent = reduce(dict.get, folders[:-1], dir_dict)
        parent[folders[-1]] = subdir
    dir_dict = dir_dict[ntpath.basename(base_dir)]
    dir_schema = get_schema(operand + "_schema", operand)
    invalid = schema_util.verify_dict_from_schema(dir_dict, dir_schema)
    return [base_dir + '/' + s for s in invalid]


def validate_yaml_with_indicators(yaml_file):
    result = {"valid": True, "result_string": ""}
    with open(yaml_file, 'r') as temp_file:
        for line in temp_file:
            if any(s in line for s in REQUIRED_INDICATORS):
                result["valid"] = False
                result["result_string"] += "Invalid value in " + yaml_file + ", line:" + line
    temp_file.close()
    return result


def validate_yaml_with_schema(yaml_file, operand):
    result = {"valid": True, "result_string": ""}
    if os.path.basename(yaml_file) != "manifest.yaml":
        if not validate_yaml_with_indicators(yaml_file)["valid"]:
            result["valid"] = False
            result["result_string"] += validate_yaml_with_indicators(yaml_file)["result_string"]
            return result
    with open(yaml_file, 'r') as temp_file:
        file_dict = {}
        try:
            file_dict = yaml.load(temp_file)
        except yaml.scanner.ScannerError:
            result["valid"] = False
            result["result_string"] += "Invalid yaml syntax  " + yaml_file + '\n'
        if file_dict:
            schema_attr_prefix = os.path.basename(yaml_file).split('.')[0]
            schema_dict = create_dict_from_schema(get_schema(get_file_schema_name(yaml_file), operand),
                                                  schema_attr_prefix, operand)
            schema_dict = schema_util.UnsortableOrderedDict({key: value for key, value in schema_dict.items()
                                                              if key is not '#'})
            if schema_dict:
                if not file_dict:
                    result["valid"] = False
                    result["result_string"] += "No content in " + yaml_file + '\n'
                else:
                    key_result = schema_util.verify_dict_keys(schema_dict, file_dict, yaml_file)
                    if not key_result["valid"]:
                        result["valid"] = False
                        result["result_string"] += key_result["result_string"]
    temp_file.close()
    return result


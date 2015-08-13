import types
import shutil
import os
import errno
from collections import OrderedDict

import yaml

from skybase.utils import dict_from_indexed_list


class UnsortableList(list):
    def sort(self, *args, **kwargs):
        pass

class UnsortableOrderedDict(OrderedDict):
    def items(self, *args, **kwargs):
        return UnsortableList(OrderedDict.items(self, *args, **kwargs))


def read_yaml_from_file(yaml_file):
    # Read YAML file and return Dictionary
    with open(yaml_file, 'r') as yf:
        return yaml.load(yf)

def write_dict_to_yaml_file(d, yaml_file):
    # Read YAML file and return Dictionary
    with open(yaml_file, 'w') as yf:
        yaml.dump(d, yf, default_flow_style=False)

def getKeyFromDict(dataDict, mapList):
    try:
        val = reduce(lambda d, k: d[k], mapList, dataDict)
    except:
        val = None
    return val

# This is just an example
def setKeyInDict(dataDict, mapList, value):
    getKeyFromDict(dataDict, mapList[:-1])[mapList[-1]] = value

def verify_dict_schema(schemaList, dataDict):
    '''
    Schema is a list of pairs of lists
    In pair 1st element is the path to the key; second element is non empty list if this path has to contain value
     e.g. [ ['definition', 'name'], ['str']
     This function only verifies the key paths, it does not operate on the values
    :param schemaList:
    :param dataDict:
    :return:
    '''
    not_found = []
    for l in schemaList:
        # TODO: allow the key value to be None or empty string
        # most likely modification in lambda: something instead of "d[k]"
        if not getKeyFromDict(dataDict, l[0]):
            path = '->'.join(l)
            not_found.append(path)
    return not_found

def verify_dict_from_schema(dict, schema):
    '''
    Schema is a list of pairs of lists
    In pair 1st element is the path to the key; second element is non empty list if this path has to contain value
     e.g. [ ['definition', 'name'], ['str']
     This function only verifies the key paths, it does not operate on the values
    :param schemaList:
    :param dataDict:
    :return:
    '''
    not_found = []
    for l in schema:
        if l[0] == ['']:
            if not dict.get(l[1][0]):
                not_found.append(l[1][0])
        else:
            val = getKeyFromDict(dict, l[0] + l[1])
            if not isinstance(val, types.DictType):
                if not val:
                    path = '/'.join(l[0] + l[1])
                    not_found.append(path)
    return not_found

def rec_dict_from_list(ll):
    if len(ll) == 1:
        return {ll[0]: ''}
    else:
        return {ll[0]: rec_dict_from_list(ll[1:])}

def rec_dict_from_list(ll, val, asList):
    if len(ll) == 1:
        if len(val) == 0 or asList:
            return {ll[0]: val}
        else:
            return {ll[0]: val[0]}
    else:
        return {ll[0]: rec_dict_from_list(ll[1:], val, False)}

def rec_dict_merge(d1, d2):
    merged = dict(d1.items() + d2.items())
    d1keys = d1.keys()

    for key in d1keys:
        # if this key is a dictionary, recurse
        if type(d1[key]) is types.DictType and d2.has_key(key):
            merged[key] = rec_dict_merge(d1[key], d2[key])

    return merged

def rec_ordered_dict_from_list(ll, val, asList):
    if len(ll) == 1:
        if len(val) == 0 or asList:
            return UnsortableOrderedDict([(ll[0], val)])
        else:
            return UnsortableOrderedDict([(ll[0], val[0])])
    else:
        return UnsortableOrderedDict([(ll[0], rec_ordered_dict_from_list(ll[1:], val, asList))])

def rec_ordered_dict_merge(d1, d2):
    merged = UnsortableOrderedDict(d1.items() + d2.items())
    d1keys = d1.keys()

    for key in d1keys:
        # if this key is a dictionary, recurse
        if type(d1[key]) is UnsortableOrderedDict and d2.has_key(key):
            merged[key] = rec_ordered_dict_merge(d1[key], d2[key])

    return merged


def verify_dict_keys(schema_dict, file_dict, file_name, key_path=''):
    result = {"valid": True, "result_string": ""}
    if (isinstance(schema_dict, str) and ("CHANGE_OR_REMOVE" in schema_dict) and file_dict == None) or\
        (isinstance(schema_dict, list) and ("CHANGE_OR_REMOVE" in schema_dict[0]) and file_dict == None):
        result["valid"] = True
        return result
    elif isinstance(schema_dict, dict) and\
        (schema_dict.get("CHANGE_OR_REMOVE_ME[DICT_ITEM_KEY]") == "CHANGE_OR_REMOVE_ME[DICT_ITEM_VALUE]"):
        result["valid"] = True
        return result
    elif (schema_dict != None and file_dict == None) or\
       (isinstance(schema_dict, list) and not isinstance(file_dict, list)) or\
       (isinstance(schema_dict, dict) and not isinstance(file_dict, dict)):
        result["valid"] = False
        result["result_string"] += "File " + file_name + " missing required key: " + key_path + "\n"
        return result
    elif isinstance(schema_dict, list):
        schema_obj = schema_dict[0]
        for child in file_dict:
            list_child_result = verify_dict_keys(schema_obj, child, file_name, key_path)
            if not list_child_result["valid"]:
                result["valid"] = False
                result["result_string"] += list_child_result["result_string"]
                return result
            key_path = key_path.rpartition('->')[0]
    elif isinstance(schema_dict, dict):
        for key in schema_dict:
            if key_path:
                key_path = key_path + '->' + key
            else:
                key_path = key
            if key == "CHANGE_ME[DICT_ITEM_KEY]" and isinstance(file_dict, dict):
                result["valid"] = True
                return result
            dict_child_result = verify_dict_keys(schema_dict[key], file_dict.get(key), file_name, key_path)
            if not dict_child_result["valid"]:
                result["valid"] = False
                result["result_string"] += dict_child_result["result_string"]
                return result
            key_path = key_path.rpartition('->')[0]
    result["valid"] = True
    return result

def copy(src, dst):
    try:
        if os.path.exists(dst):
            delete(dst)
        shutil.copytree(src, dst)
    except OSError as e:
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dst)

def delete(fileOrDirToDelete):
    if os.path.isdir(fileOrDirToDelete):
        shutil.rmtree(fileOrDirToDelete)
    else:
        if (os.path.exists(fileOrDirToDelete)):
            os.remove(fileOrDirToDelete)

def convert_stack_roles_to_dict(stacks_as_list):
    # convert deployment stack collection from native list to dict form
    stack_roles_as_dict = dict()

    # TODO: derive dict keys 'name', 'roles' from skybase schema main_deployment_stacks_yaml_schema
    if stacks_as_list:
        # convert list of stacks to dict
        stacks_as_dict = dict_from_indexed_list('name', stacks_as_list)

        # iterate through all stacks and convert role collection from list to dict
        for stack, values in stacks_as_dict.items():
            # convert list of roles within stack to dict
            roles_as_dict = dict_from_indexed_list('name', values['roles'])

            # replace roles as list with dict
            values['roles'] = roles_as_dict

            # add stack to collection
            stack_roles_as_dict[stack] = values

    return stack_roles_as_dict

if __name__ == '__main__':

    my_schema = [
        ['name'],
        ['services'],
        ['services', 'consul']
    ]
    my_dict = {
        'name': 'my_name',
        'universe': 'dev',
        # 'services': {
        #     'test': 'x'
        # }
    }

    print verify_dict_schema(my_schema, my_dict)


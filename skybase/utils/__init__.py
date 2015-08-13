import os
import sys
import datetime
import contextlib
import tempfile
import shutil
import errno
import ConfigParser
import string
import subprocess
import tarfile
import json

def simple_error_format(e):
    return "{0}: {1}".format(type(e).__name__, str(e))

def basic_timestamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)

def mkdir_path(path):
    # attempt to make directory path.  ignore error if directory exists
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def dict_from_indexed_list(key, coll_as_list):
    coll_as_dict = dict()
    for stack in coll_as_list:
        coll_as_dict[stack[key]] = stack
    return coll_as_dict

def parse_config_file(profile, config_file, config_attrs):

    # verify config file exists and is readable
    config_file_exists = os.path.isfile(config_file)
    if not config_file_exists:
        raise IOError('{0}: file not found'.format(config_file))

    config_file_is_readable = os.access(config_file, os.R_OK)
    if not config_file_is_readable:
        raise IOError('{0}: read permission denied'.format(config_file))

    # parse configuration file
    cfgprs = ConfigParser.ConfigParser()
    cfgprs.read(config_file)

    # retrieve requested configuration attribute values
    acct_profile = 'profile ' + profile
    config = {attr: cfgprs.get(acct_profile, attr) for attr in config_attrs}

    return config

def strtobool (val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = string.lower(val)
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError, "invalid truth value %r" % (val,)


def run_subproc(cmd, env):
    # initialize subprocess using provided or current os environment
    proc = subprocess.Popen(cmd,
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    # execute knife command as subprocess trapping standard output and error
    stdout_value, stderr_value = proc.communicate()
    return stdout_value, stderr_value

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def merge_list_of_dicts(list_of_dicts):
    merged_dicts = {}
    for d in list_of_dicts:
        merged_dicts.update(d)
    return merged_dicts

def user_yes_no_query(question):
    while True:
        try:
            sys.stdout.write('%s [y/n]: ' % question)
            return strtobool(raw_input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

def extract_tar_file(target_dir, tar_file, mode='r:gz'):
    with tarfile.open(tar_file, mode) as tar:
        tar.extractall(path=target_dir)

def all_true(blob):
    return bool(reduce(lambda x, y: x*y, blob))

def json_pretty_print(output, indent=2, separators=(',', ': ')):
    return json.dumps(output, indent=indent, separators=separators)
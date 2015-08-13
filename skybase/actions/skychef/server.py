import os
import tempfile
import json

from skybase.utils import run_subproc
from skybase import config as sky_cfg


def prepare_knife_env(planet, config=None):
    if not config:
        config = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)

    # add skybase PLANET_PATH env var to copy of current shell environment
    knife_env = os.environ.copy()
    knife_env['CHEF_CREDS_PATH'] = os.path.join(
        config.data['runner_credentials_dir'],
        'chef',
        planet.planet_name,)
    return knife_env


def cookbook_upload(planet, service, config):
    # prepare and execute knife command for each cookbook in list
    result = []
    for cookbook in service.install.ordered_cookbooks:
        # prepare knife cookbook upload command as list
        knife_cmd = ['knife', 'cookbook', 'upload',
                     '--config', planet.get_knife_file(),
                     '--cookbook-path', service.install.cookbook_path,
                     cookbook]

        # execute knife command as subprocess trapping standard output and error
        stdout_value, stderr_value = run_subproc(knife_cmd,
                                                 env=prepare_knife_env(planet, config))

        # report command execution output
        result.append({
            cookbook: {
                'stdout': stdout_value,
                'stderr': stderr_value,
            }
        })

    return result


def environment_create(chef_env_attr, planet, config):
    # create temporary file to be based to knife cmd
    try:

        with tempfile.NamedTemporaryFile(suffix='.json') as env_attr_file:
            # write attributes to temp file as JSON
            env_attr_file.write(json.dumps(chef_env_attr))
            env_attr_file.seek(0)

            # prepare knife cookbook upload command as list
            knife_cmd = ['knife', 'environment', 'from', 'file',
                         '--config', planet.get_knife_file(),
                         env_attr_file.name]

            # execute knife command as subprocess trapping standard output and error
            stdout_value, stderr_value = run_subproc(knife_cmd,
                                                     env=prepare_knife_env(planet, config))

            result = {'stdout': stdout_value, 'stderr': stderr_value}

    except Exception as e:
        result = {type(e).__name__: str(e)}

    return result


def role_create(chef_role_attr, planet, config):
    # create temporary file to be based to knife cmd
    with tempfile.NamedTemporaryFile(suffix='.json') as role_attr_file:
        # write attributes to temp file as JSON
        role_attr_file.write(json.dumps(chef_role_attr))
        role_attr_file.seek(0)

        # prepare knife cookbook upload command as list
        knife_cmd = ['knife', 'role', 'from', 'file',
                     '--config', planet.get_knife_file(),
                     role_attr_file.name]

        # execute knife command as subprocess trapping standard output and error
        stdout_value, stderr_value = run_subproc(knife_cmd,
                                                 env=prepare_knife_env(planet, config))

        result = {
            'stdout': stdout_value,
            'stderr': stderr_value,
        }

    return result


def databag_create(databag_list, planet, config):
    # prepare and execute knife command for each databag in list
    result = dict()

    # upload databags for un/encrypted databag directories
    for databag_collection in databag_list:
        # acquire absolute path to databag directory
        databag_abs_path = databag_collection.values()[0]['path']

        # run knife command on each databag found in directory
        for databag in databag_collection.values()[0]['databags']:

            # prepare knife command to create databag
            knife_cmd = ['knife', 'data', 'bag', 'create', databag,
                         '--config', planet.get_knife_file()]

            # execute knife command as subprocess trapping standard output and error
            stdout_value, stderr_value = run_subproc(knife_cmd,
                                                     env=prepare_knife_env(planet, config))

            # gather command execution results per databag
            result[databag] = {
                'create': {'stdout': stdout_value, 'stderr': stderr_value}
            }

            # prepare knife command to upload databag items
            knife_cmd = ['knife', 'data', 'bag', 'from', 'file',
                         databag, os.path.join(databag_abs_path, databag),
                         '--config', planet.get_knife_file()]

            # execute knife command as subprocess trapping standard output and error
            stdout_value, stderr_value = run_subproc(knife_cmd,
                                                     env=prepare_knife_env(planet, config))

            # gather command execution results per databag
            result[databag]['items'] = {'stdout': stdout_value,
                                        'stderr': stderr_value}

    return result
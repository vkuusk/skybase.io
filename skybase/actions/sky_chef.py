import os
import subprocess
import tempfile
import json
import logging
import skybase.exceptions


def prepare_knife_env(knife_env_path):
    # add skybase PLANET_PATH env var to copy of current shell environment
    knife_env = os.environ.copy()
    knife_env['PLANET_PATH'] = knife_env_path
    return knife_env


def cookbook_upload(knife_env_path, knife_config_path, cookbooks_path, cookbook, logger):
    # prepare and execute knife command for each cookbook in list
    result = []

    # prepare knife cookbook upload command as list
    knife_cmd = ['knife', 'cookbook', 'upload',
                 '--config', knife_config_path,
                 '--cookbook-path', cookbooks_path,
                 cookbook]

    # execute knife command as subprocess trapping standard output and error
    logger.write('Running knife cookbook upload --config ' + knife_config_path + ' --cookbook-path ' + cookbooks_path +
                 ' ' + cookbook)
    proc = subprocess.Popen(knife_cmd, env=prepare_knife_env(knife_env_path),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_value, stderr_value = proc.communicate()

    result.append({
        cookbook: {
            'stdout': stdout_value,
            'stderr': stderr_value,
        }
    })

    return result


def environment_create(knife_env_path, knife_config_path, chef_env_attr):
    result = {"valid": True, "result_string": ""}
    # create temporary file to be based to knife cmd
    try:
        with tempfile.NamedTemporaryFile(suffix='.json', dir=os.getcwd()) as env_attr_file:
            # create name and description for environment
            chef_env_attr['name'] = chef_env_attr['definition']['planet']
            chef_env_attr['description'] = 'The ' + chef_env_attr['name'] + ' planet'
            # write attributes to temp file as JSON
            env_attr_file.write(json.dumps(chef_env_attr))
            env_attr_file.seek(0)

            # prepare knife cookbook upload command as list
            knife_cmd = ['knife', 'environment', 'from', 'file',
                         '--config', knife_config_path,
                         env_attr_file.name]

            # execute knife command as subprocess trapping standard output and error
            result["result_string"] += 'Running knife environment from file --config ' + knife_config_path + ' ' + \
                                       env_attr_file.name + '\n'
            proc = subprocess.Popen(knife_cmd, env=prepare_knife_env(knife_env_path),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout_value, stderr_value = proc.communicate()
            rc = proc.returncode
            if rc is not 0:
                result["valid"] = False
            result["result_string"] += "stdout: " + stdout_value + "\nstderr: " + stderr_value

    except Exception as e:
        result["result_string"] += "Exception: " + str(e)
        result["valid"] = False

    return result


def _run_knife_command(knife_cmd, knife_env=None, logger=None):
    result = []

    env = os.environ.copy()
    if knife_env is not None:
        env.update(knife_env)

    if logger:
        logger.debug('Running "%s"' % ' '.join(knife_cmd))

    # execute knife command as subprocess trapping standard output and error
    proc = subprocess.Popen(
        knife_cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout_value, stderr_value = proc.communicate()

    stdout_value.strip()
    stderr_value.strip()
    returncode = proc.returncode

    if logger:
        logger.debug('stdout (%s): %s' % (returncode, stdout_value))
        logger.debug('stderr (%s): %s' % (returncode, stderr_value))

    if returncode is not 0:
        raise skybase.exceptions.SkyBaseResponseError("knife returned a non-zero exit code (%s): %s" % (returncode, stderr_value))

    result.append(
        {'output': stdout_value}
    )

    return result


def get_node(planet, node, logger=None):
    # prepare and execute knife command
    knife_cmd = [
        'knife',
        'node',
        'show',
        '--config',
        os.path.join(planet.planet_data_dir, 'knife.rb'),
        '--format',
        'json',
        node
    ]

    knife_env = os.environ.copy()
    knife_env.update(planet.get_chef_knife_attributes())

    return _run_knife_command(knife_cmd, knife_env, logger)


def delete_node(planet, node, logger=None):
    # prepare and execute knife command
    knife_cmd = [
        'knife',
        'node',
        'delete',
        '--config',
        os.path.join(planet.planet_data_dir, 'knife.rb'),
        '--yes',
        node
    ]

    knife_env = os.environ.copy()
    knife_env.update(planet.get_chef_knife_attributes())

    return _run_knife_command(knife_cmd, knife_env, logger)

def get_role(planet, role, logger=None):
    # prepare and execute knife command
    knife_cmd = [
        'knife',
        'role',
        'show',
        '--config',
        os.path.join(planet.planet_data_dir, 'knife.rb'),
        '--format',
        'json',
        role
    ]

    knife_env = os.environ.copy()
    knife_env.update(planet.get_chef_knife_attributes())

    return _run_knife_command(knife_cmd, knife_env, logger)

def delete_role(planet, role, logger=None):
    # prepare and execute knife command
    knife_cmd = [
        'knife',
        'role',
        'delete',
        '--config',
        os.path.join(planet.planet_data_dir, 'knife.rb'),
        '--yes',
        role
    ]

    knife_env = os.environ.copy()
    knife_env.update(planet.get_chef_knife_attributes())

    return _run_knife_command(knife_cmd, knife_env, logger)

def delete_client(planet, client, logger=None):
    # prepare and execute knife command
    knife_cmd = [
        'knife',
        'client',
        'delete',
        '--config',
        os.path.join(planet.planet_data_dir, 'knife.rb'),
        '--yes',
        client
    ]

    knife_env = os.environ.copy()
    knife_env.update(planet.get_chef_knife_attributes())

    return _run_knife_command(knife_cmd, knife_env, logger)

import os

from . import server
from . import solo

import skybase.actions.sky_chef
import skybase.actions.skycloud
import skybase.actions.salt
from skybase.api.salt import SkySaltAPI
from skybase.service.state import ServiceRegistryRecord
from skybase.utils import simple_error_format

def chef_update(planet, service, runtime, config=None):

    result = []

    # TODO: allow for artiball 'chef_type' attribute to be missing and not default to 'server'
    # validate artiball's chef_type, defaulting to server
    chef_type = service.deploy.definition.get('chef_type', 'server')
    if chef_type in ['server', 'solo']:
        result.append({'chef_type': chef_type})
    else:
        return {'chef_type': chef_type, 'message': 'chef_type unsupported'}

    # upload chef cookbooks
    try:
        result.append({'cookbook_upload': cookbook_upload(chef_type, planet, service, runtime, config)})
    except Exception as e:
        result.append({'cookbook_upload': str(e)})

    # upload chef roles for each stack
    try:
        stack_role_result = {}
        # TODO: push iteration into main chef_role_create procedure
        # create role attributes for each stack in launch list
        for stack_id in service.deploy.stack_launch_list:
            try:
                stack_role_result[stack_id] = role_create(chef_type, stack_id, planet, service, runtime, config)
            except Exception as e:
                stack_role_result[stack_id] = str(e)

        result.append({'role_create': stack_role_result})
    except Exception as e:
        result.append({'role_create': str(e)})

    # upload chef databags
    try:
        result.append({'databag_upload': databag_create(chef_type, planet, service, runtime, config)})
    except Exception as e:
        result.append({'databag_upload': str(e)})

    # upload chef environment
    try:
        result.append({'environment_create': environment_create(chef_type, planet, service, runtime, config)})
    except Exception as e:
        result.append({'environment_create': str(e)})

    return result


def cookbook_upload(chef_type, planet, service, runtime, config):
    result = dict()

    # return list of cookbooks if not applying release
    result['cookbooks'] = service.install.cookbooks

    # upload cookbooks to provider object store
    if runtime.apply:
        result['solo'] = solo.cookbook_upload(planet, service, runtime)

        # upload to chef server if indicated
        if chef_type == 'server':
            result['server'] = server.cookbook_upload(planet, service, config)

    return result


def environment_create(chef_type, planet, service, runtime, config):

    # JSON template for chef env attributes
    chef_env_attr = planet.chef_env_attr

    # initialize default result
    result = {
        'planet': planet.planet,
        'chef_env_attr': chef_env_attr,
    }

    # upload environment to provider object store
    if runtime.apply:
        result['solo'] = solo.environment_create(chef_env_attr, planet, service, runtime)

    return result

def make_chef_role_name(role_name, deploy_tag):
    # TODO: revisit composition of chef role name to add service and stack
    chef_role_name = '{0}-{1}'.format(role_name, deploy_tag)
    return chef_role_name

def role_create(chef_type, stack_id, planet, service, runtime, config):

    # prepare results container
    result = dict()

    # collect chef role attributes for all stack roles
    for role_name in service.deploy.get_stack_roles(stack_id):
        # resolve chef role attributes for this role
        chef_role_name = make_chef_role_name(role_name, runtime.tag)
        chef_role_attr = service.get_role_attributes(stack_id, role_name, chef_role_name, planet.universe, planet.planet)

        # initialize container for role and initialize with derived role attributes
        result[chef_role_name] = dict()
        result[chef_role_name]['role_attributes'] = chef_role_attr

        if runtime.apply:
            # upload role to provider object store
            result[chef_role_name]['solo'] = solo.role_create(chef_role_attr, stack_id, role_name, planet, service, runtime)

            # upload to chef server if indicated
            if chef_type == 'server':
                result[chef_role_name]['server'] = server.role_create(chef_role_attr, planet, config)

    return result


def databag_create(chef_type, planet, service, runtime, config):
    # initialize result container
    result = {'databags': dict()}

    databag_list = []

    # append directory names from unencrypted databags directory
    if service.install.databags:
        databag_list.append(
            {service.install.databags_dir:
                    {'databags': service.install.databags,
                     'path': service.install.databags_path},
            })
        result['databags'][service.install.databags_dir] = service.install.databags

    # append directory names from encrypted databags directory
    if service.install.encrypted_databags:
        databag_list.append(
            {service.install.enc_databags_dir:
                    {'databags': service.install.encrypted_databags,
                     'path': service.install.enc_databags_path},
            })
        result['databags'][service.install.enc_databags_dir] = service.install.encrypted_databags

    if runtime.apply and len(databag_list) > 0:
        # upload to provider object store
        result['solo'] = solo.databag_create(databag_list, planet, service, runtime)

        # upload to chef server if indicated
        if chef_type == 'server':
            result['server'] = server.databag_create(databag_list, planet, config)

    return result

def delete_stack_chef_roles(planet, runtime, stacks):

    result = dict()

    for skybase_stack_id in stacks.keys():

        skybase_id, stack_name = os.path.split(skybase_stack_id)
        service = ServiceRegistryRecord.init_from_id(skybase_id)

        for role in service.blueprint.stacks[stack_name]['roles']:

            chef_role_name = make_chef_role_name(
                role_name=role,
                deploy_tag=service.tag,
            )

            try:
                if runtime.apply:
                    if skybase.actions.skycloud.is_stack_deleted_or_not_found(planet, stack_name):
                        result[chef_role_name] = skybase.actions.sky_chef.delete_role(planet=planet, role=chef_role_name)
                    else:
                        result[chef_role_name] = 'stack {0} exists.  cannot delete chef role {1}'.format(stack_name, chef_role_name)
                else:
                    result[chef_role_name] = skybase.actions.sky_chef.get_role(planet=planet, role=chef_role_name)
            except Exception as e:
                result[chef_role_name] = simple_error_format(e)

    return result

def get_stack_chef_nodes(skybase_stack_id, runner_cfg):

    skybase_id, stack_name = os.path.split(skybase_stack_id)

    service = ServiceRegistryRecord.init_from_id(skybase_id)
    stack_grain = service.stacks.stacks[stack_name].salt_grain_skybase_id

    authtoken = skybase.actions.salt.get_saltapi_authtoken(runner_cfg=runner_cfg, planet_name=service.planet)
    saltapi_result = skybase.actions.salt.get_host_by_grain(
        grain=stack_grain,
        authtoken=authtoken,
        planet_name=service.planet,
    )

    # extract host/instance id from  non-empty result that contains minion data
    result = []
    if saltapi_result[0] and saltapi_result[0] != SkySaltAPI.NO_MINIONS:
        for minion in saltapi_result:
            if 'host' in minion.values()[0]:
                result.append(minion.values()[0]['host'])

    return result

def delete_stack_chef_nodes(planet, runtime, stack_nodes):
    result = dict()

    for stack_name, nodes in stack_nodes.items():
        result[stack_name] = dict()
        if runtime.apply:
            if skybase.actions.skycloud.is_stack_deleted_or_not_found(planet, stack_name):
                result[stack_name]['delete_chef_nodes'] = delete_chef_nodes(planet=planet, runtime=runtime, nodes=nodes)
            else:
                result[stack_name] = 'stack {0} exists.  cannot delete chef nodes {1}'.format(stack_name, nodes)
        else:
            result[stack_name]['get_node'] = get_chef_nodes(planet=planet, nodes=nodes)

    return result

def delete_chef_nodes(planet, runtime, nodes):
    result = dict()

    for node in nodes:
        result[node] = dict()
        try:
            if runtime.apply:
                try:
                    result[node]['delete_node'] = skybase.actions.sky_chef.delete_node(planet=planet, node=node)
                except Exception as e:
                    result[node]['delete_node'] = simple_error_format(e)
                else:
                    try:
                        result[node]['delete_client'] = skybase.actions.sky_chef.delete_client(planet=planet, client=node)
                    except Exception as e:
                        result[node]['delete_client'] = simple_error_format(e)
            else:
                result[node]['get_node'] = skybase.actions.sky_chef.get_node(planet=planet, node=node)

        except Exception as e:
            result[node] = simple_error_format(e)

    return result

def get_chef_nodes(planet, nodes):
    result =  dict()
    for node in nodes:
        try:
            result[node] = skybase.actions.sky_chef.get_node(planet, node)
        except Exception as e:
            result[node] = simple_error_format(e)
    return result

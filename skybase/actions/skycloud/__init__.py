import os

import yaml
import json

import heatclient.exc
import boto.exception

from . import aws
from . import openstack
from . import renderer
from skybase.artiball import ARTIBALL_SCHEMA_ARGS
from skybase.utils import make_temp_directory

def launch_stacks(planet=None,
                  service=None,
                  runtime=None,
                  system=None,):

    # initialize response values
    response = {
        'planet': planet.planet_name,
        'universe': planet.universe,
        'provider': planet.provider,
        'stacks': None
    }

    if not runtime.apply:
        response['stacks'] = service.deploy.stack_launch_list
        response['runtime'] = str(runtime)
        return response

    # collect cloud templates for each stack in launch list
    cloud_template_list = []

    # filter stack launch list if runtime value present
    for stack_id in service.deploy.stack_launch_list:

        # create stack launch name
        stack_launch_name = create_stack_launch_name(
            service_id=service.deploy.definition['service_name'],
            tag=runtime.tag,
            stack_id=stack_id
        )

        cloud_template_list.append(
            renderer.CloudTemplate(
                planet=planet,
                service=service,
                runtime=runtime,
                system=system,
                stackname=stack_id,
                **{'stack_launch_name': stack_launch_name})
        )

    # prepare result container
    call_cloud_api_result = dict()

    # call cloud service api for each stack template
    for template in cloud_template_list:

        try:
            call_cloud_api_result[template.stackname] = {
                'id': call_cloud_api(
                    planet=planet,
                    stack_name=template.stack_launch_name,
                    action='create_stack',
                    template_body=template.template_body,
                    parameters=service.get_template_params()),

                'name': template.stack_launch_name,
            }

        except Exception as e:
            call_cloud_api_result[template.stackname] = str(e)

    # add stack launch info to response
    response['stacks'] = call_cloud_api_result

    return response


def create_stack_launch_name(service_id, tag, stack_id=None):
    if stack_id:
        return '-'.join([str(service_id), str(tag), str(stack_id)])
    else:
        return '-'.join([str(service_id), str(tag)])


def get_cloud_conn(planet):
    # provide cloud connection based upon provider
    cloud_conn_switch = {
        'aws': lambda: aws.get_cloud_conn(planet),
        'openstack': lambda: openstack.get_cloud_conn(planet),
        }
    return cloud_conn_switch.get(planet.provider, lambda: None)()


def call_cloud_api(planet,
                   stack_name,
                   action,
                   template_body=None,
                   parameters=None):

    # call provider cloud api
    cloud_api_switch = {
        'aws': lambda: aws.call_cloud_api(planet,
                                          stack_name,
                                          action,
                                          template_body,
                                          parameters),


        'openstack': lambda: openstack.call_cloud_api(planet,
                                                      stack_name,
                                                      action,
                                                      template_body,
                                                      parameters),
        }
    return cloud_api_switch.get(planet.provider, lambda: None)()


def delete_stacks(planet=None,
                  runtime=None,
                  stacks=None):

    # initialize response values
    response = {
        'planet': planet.planet_name,
        'stacks': stacks,
        'apply': runtime.apply
    }

    if not runtime.apply:
        return response

    # prepare result container
    cloud_api_result = dict()

    # call cloud service api for each stack template
    for stack in stacks:
        try:
            cloud_api_result[stack] = call_cloud_api(
                planet=planet,
                stack_name=stack,
                action='delete_stack',
                )
        except Exception as e:
            cloud_api_result[stack] = str(e)

    # add stack launch info to response
    response['stacks'] = str(cloud_api_result)
    return response


def are_stacks_valid(orchestration_engine, stacks):
    '''
    :param orchestration_engine: valid value from Planet()
    :param stacks: list of stacks
    :return: multiple all boolean values together to produce single T/F for list
    '''
    # call provider cloud api
    stacks_valid_switch = {
        'cfn': lambda: aws.are_stacks_valid(stacks),
        'heat': lambda: openstack.are_stacks_valid(stacks)
    }

    return stacks_valid_switch.get(orchestration_engine, lambda: None)()

def package_transfer(planet=None, service=None, runtime=None, system=None):
    '''wrapper function to upload app directory contents both as tar archive
    and individual files to object store'''
    result = dict()
    result['app_file_upload'] = app_files_upload(planet, service, runtime, system)
    result['app_dir_upload'] = app_dir_upload(planet, service, runtime, system)
    return result

def app_files_upload(planet=None, service=None, runtime=None, system=None):

    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    # initialize results container
    result = {
        'packages': service.app.packages,
        'prov_obj_store_type': prov_obj_store_type,
    }

    # upload tar file for each stack-role to provider object store
    if runtime.apply:
        # upload packages for each stack-role to provider object store
        for stack_id in service.deploy.stack_launch_list:
            # initialize stack results container
            result[stack_id] = dict()

            for role_name in service.deploy.get_stack_roles(stack_id):
                # initialize role results container
                result[stack_id][role_name] = dict()
                result[stack_id][role_name]['local_to_object_store_copy'] = dict()

                for package in service.app.packages:
                    # copy local package files to object store namespace
                    result[stack_id][role_name]['local_to_object_store_copy'][package] = local_to_object_store_copy(
                        obj_store_type=prov_obj_store_type,
                        planet=planet,
                        key_path='/'.join([get_target_path(planet, service, runtime, stack_id, role_name), ARTIBALL_SCHEMA_ARGS.get('code_dir'), package]),
                        local_file=os.path.join(service.app.app_path, package)
                    )

    return result

def app_dir_upload(planet=None, service=None, runtime=None, system=None):

    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    # initialize results container
    result = {
        'packages': service.app.packages,
        'prov_obj_store_type': prov_obj_store_type,
    }

    if runtime.apply:
        # archive and upload contents of artiball app folder to provider object store
        for stack_id in service.deploy.stack_launch_list:
            # initialize stack results container
            result[stack_id] = dict()

            for role_name in service.deploy.get_stack_roles(stack_id):
                # initialize role results container
                result[stack_id][role_name] = dict()

                # upload content of artiball app folder to s3 as tar.gz archive
                result[stack_id][role_name]['upload_to_object_store'] = upload_to_object_store(
                    obj_store_type = prov_obj_store_type,
                    local_tar_src=service.app.app_path,
                    planet=planet,
                    key_path=get_target_path(planet, service, runtime, stack_id, role_name),
                    archive_file='app.tar.gz')

    return result

def salt_grains_transfer(planet=None, service=None, runtime=None, system=None):

    salt_grain_filename = 'grains'

    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    result = dict()

    for stack_id in service.deploy.stack_launch_list:
        result[stack_id] = dict()

        for role_name in service.deploy.get_stack_roles(stack_id):

            skybase_id = '-'.join([
                planet.definition['planet'],
                service.metadata['app_name'],
                runtime.tag,
                stack_id,
                role_name,
            ])

            # generate custom salt grains for minion
            minion_grains = {
                'skybase': {
                    'skybase_id': skybase_id,
                    'planet': planet.definition['planet'],
                    'service': service.metadata['app_name'],
                    'tag': runtime.tag,
                    'stack': stack_id,
                    'role': role_name,
                    'version': service.metadata['app_version'],
                    'build': service.metadata['build_id'],
                    'source_artiball': service.metadata['source_artiball'],
                }
            }

            # initialze results container for stack/role
            result[stack_id][role_name] = dict()
            result[stack_id][role_name]['grains'] = minion_grains

            # upload grains to service namespace
            if runtime.apply:

                # create temporary directory and file
                with make_temp_directory() as tdir:

                    with open(os.path.join(tdir, salt_grain_filename), 'w') as grains_file:
                        # dump salt grains as YAML file and reset file marker to top
                        grains_file.write(yaml.safe_dump(minion_grains, default_flow_style=False))
                        grains_file.seek(0)

                        # generate service namespace path to salt folder
                        key_path = '{0}/{1}'.format(
                            get_target_path(planet, service, runtime, stack_id, role_name),
                            'salt'
                        )

                        # upload grains archive file to provider object store
                        result[stack_id][role_name]['upload_to_object_store'] = upload_to_object_store(
                            obj_store_type = prov_obj_store_type,
                            local_tar_src=grains_file.name,
                            planet=planet,
                            key_path=key_path,
                            archive_file='grains.tar.gz')

    return result

def upload_to_object_store(obj_store_type, local_tar_src, planet, key_path, archive_file):

    # registry of supported upload options for predefined object storage types
    object_store_upload_options = {

        's3': lambda: aws.upload_to_object_store(
            local_tar_src=local_tar_src,
            profile=planet.services['prov-object-store']['profile'],
            bucket_name=planet.services['prov-object-store']['bucket'],
            key_path=key_path,
            archive_file=archive_file),

        'swift': lambda: openstack.upload_to_object_store(
            local_tar_src=local_tar_src,
            profile=planet.services['prov-object-store']['profile'],
            endpoint=planet.definition['api_endpoints']['object_store'],
            container=planet.services['prov-object-store']['bucket'],
            path=key_path,
            archive_file=archive_file),
        }

    # executue object storage upload function for provided type
    return object_store_upload_options.get(obj_store_type, lambda: None)()

def local_to_object_store_copy(obj_store_type, planet, key_path, local_file):
    # registry of supported copy options for predefined object storage types
    object_store_copy_options = {

        's3': lambda: aws.local_to_object_store_copy(
            profile=planet.services['prov-object-store']['profile'],
            bucket_name=planet.services['prov-object-store']['bucket'],
            key_path=key_path,
            local_file=local_file),

        'swift': lambda: openstack.local_to_object_store_copy(
            profile=planet.services['prov-object-store']['profile'],
            endpoint=planet.definition['api_endpoints']['object_store'],
            container=planet.services['prov-object-store']['bucket'],
            path=key_path,
            local_file=local_file),
        }

    # execute object storage copy function for provided type
    return object_store_copy_options.get(obj_store_type, lambda: None)()

def get_target_path(planet, service, runtime, stack_id, role_name):
    # create unique object storage path
    path = os.path.join(
        planet.services['prov-object-store']['url'],
        service.manifest['app_name'],
        runtime.tag,
        stack_id,
        role_name)
    return path


def list_objects(planet, key_path,):
    # registry of supported object storage providers
    list_objects_options = {
        's3': lambda: aws.list_objects(
            profile=planet.services['prov-object-store']['profile'],
            bucket_name=planet.services['prov-object-store']['bucket'],
            key_path=key_path, ),

        'swift': lambda: openstack.list_objects(
            profile=planet.services['prov-object-store']['profile'],
            endpoint=planet.definition['api_endpoints']['object_store'],
            container=planet.services['prov-object-store']['bucket'],
            prefix=key_path,
        ),
    }

    # execute object storage upload function for provided type
    return list_objects_options.get(planet.services['prov-object-store']['type'], lambda: None)()

def delete_objects(planet, key_path,):
    # registry of supported object storage providers
    delete_objects_options = {
        's3': lambda: aws.delete_objects(
            profile=planet.services['prov-object-store']['profile'],
            bucket_name=planet.services['prov-object-store']['bucket'],
            key_path=key_path, ),

        'swift': lambda: openstack.delete_objects(
            profile=planet.services['prov-object-store']['profile'],
            endpoint=planet.definition['api_endpoints']['object_store'],
            container=planet.services['prov-object-store']['bucket'],
            prefix=key_path,
        ),
    }

    # execute object storage upload function for provided type
    return delete_objects_options.get(planet.services['prov-object-store']['type'], lambda: None)()

#TODO: create provider specific versions for aws/openstack
def is_stack_deleted_or_not_found(planet, stack_name):
    try:
        # retrieve stack status
        stack_status = call_cloud_api(
            planet=planet,
            stack_name=stack_name,
            action='get_stack_status')

        # verify cloud provider DELETE* status for stack id
        result = stack_status.startswith('DELETE')

    except heatclient.exc.HTTPNotFound as e:
        # stack not found OK for delete
        heat_exc_msg = json.loads(e.message)
        result = 'code' in heat_exc_msg and heat_exc_msg['code'] == 404

    except boto.exception.BotoServerError as e:
        result = e.message.startswith('Stack') and e.message.endswith('does not exist')

    return result

def delete_stack_objects(planet=None,
                  runtime=None,
                  stacks=None):

    # initialize response values
    response = {
        'planet': planet.planet_name,
        'apply': runtime.apply
    }

    # prepare result container
    delete_objects_result = dict()

    # attempt to delete stack objects by stack name
    for skybase_id, stack_info in stacks.items():

        key_path = 'planets{0}'.format(skybase_id)
        stack_name = stack_info['stack_name']

        if runtime.apply:
            if is_stack_deleted_or_not_found(planet, stack_name):
                delete_objects_result[stack_name] = delete_objects(
                    planet=planet,
                    key_path=key_path,
                )
            else:
                delete_objects_result[stack_name] = 'stack {0} exists.  cannot delete stack object storage'.format(stack_name)
        else:
            # only list stack objects if non-apply
            delete_objects_result[stack_name] = list_objects(
                planet=planet,
                key_path=key_path,
            )

    # add stack launch info to response
    response['stacks'] = delete_objects_result
    return response
import json
import os
import tarfile

import skybase.utils

from skybase.actions.skycloud import get_target_path, upload_to_object_store, local_to_object_store_copy


def cookbook_upload(planet, service, runtime):

    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    # initialize results container
    result = dict()

    # upload tar file for each stack-role to provider object store
    for stack_id in service.deploy.stack_launch_list:
        result[stack_id] = dict()

        for role_name in service.deploy.get_stack_roles(stack_id):

            result[stack_id][role_name] = {'prov_obj_store_type': prov_obj_store_type}

            result[stack_id][role_name]['upload_to_object_store'] = upload_to_object_store(
                obj_store_type = prov_obj_store_type,
                local_tar_src=service.install.cookbook_path,
                planet=planet,
                key_path=get_target_path(planet, service, runtime, stack_id, role_name),
                archive_file='cookbooks.tar.gz')

    return result


def environment_create(chef_env_attr, planet, service, runtime):
    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    # initalize results container
    result = dict()

    # create temporary directory and file
    with skybase.utils.make_temp_directory() as tdir:
        with open(os.path.join(tdir, (planet.planet + '.json')), 'w') as env_attr_file:
            # dump chef environment attributes as JSON
            env_attr_file.write(json.dumps(chef_env_attr))
            env_attr_file.seek(0)

            # upload tar file for each stack-role to provider object store
            for stack_id in service.deploy.stack_launch_list:
                result[stack_id] = dict()

                for role_name in service.deploy.get_stack_roles(stack_id):

                    result[stack_id][role_name] = {
                        'prov_obj_store_type': prov_obj_store_type
                    }

                    result[stack_id][role_name]['upload_to_object_store'] = upload_to_object_store(
                        obj_store_type = prov_obj_store_type,
                        local_tar_src=env_attr_file.name,
                        planet=planet,
                        key_path=get_target_path(planet, service, runtime, stack_id, role_name),
                        archive_file=planet.planet + '.tar.gz')

    return result


def role_create(chef_role_attr, stack_id, role_name, planet, service, runtime):
    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    # initalize results container
    result = dict()

    # create temporary directory and file
    with skybase.utils.make_temp_directory() as tdir:
        with open(os.path.join(tdir, (role_name + '.json')), 'w') as role_attr_file:
            # dump chef role attributes as JSON
            role_attr_file.write(json.dumps(chef_role_attr))
            role_attr_file.seek(0)

            # upload tar file for stack-role to provider object store
            result['upload_to_object_store'] = upload_to_object_store(
                obj_store_type = prov_obj_store_type,
                local_tar_src=role_attr_file.name,
                planet=planet,
                key_path=get_target_path(planet, service, runtime, stack_id, role_name),
                archive_file=role_name + '.tar.gz')

    return result


def databag_create(databag_list, planet, service, runtime):
    # target filename to be dropped onto new instance
    tarfile_name = 'databags.tar.gz'

    # retrieve provision object storage type
    prov_obj_store_type = planet.services['prov-object-store'].get('type')

    # initalize results container
    result = dict()

    # determine active stacks for launch
    for stack_id in service.deploy.stack_launch_list:
        result[stack_id] = dict()

        # upload tar file for each stack-role to provider object store
        for role_name in service.deploy.get_stack_roles(stack_id):
            result[stack_id][role_name] = {'prov_obj_store_type': prov_obj_store_type}

            # create a temporary working directory holding databag tarfile
            with skybase.utils.make_temp_directory() as tdir:
                target_filename = os.path.join(tdir, tarfile_name)

                with tarfile.open(target_filename, mode="w:gz") as tar:

                    for databag_collection in databag_list:
                        db_path = databag_collection.values()[0]['path']
                        tar.add(db_path, arcname='databags')

                # copy tar file to object storage
                result[stack_id][role_name]['upload_to_object_store'] = local_to_object_store_copy(
                    obj_store_type=prov_obj_store_type,
                    planet=planet,
                    key_path='/'.join([get_target_path(planet, service, runtime, stack_id, role_name), tarfile_name]),
                    local_file=target_filename
                )

    return result
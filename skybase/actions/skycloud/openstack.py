import os

import httplib

import heatclient.client
import keystoneclient.v2_0.client as ksclient
import keystoneclient.openstack.common.apiclient.exceptions as KeyStoneExceptions
import heatclient.client
import swiftclient
import swiftclient.exceptions
import novaclient.client

from skybase import config as sky_cfg
import skybase.exceptions
import skybase.utils

def get_config_file(config_dir=None):
    if not config_dir:
        runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)
        config_dir = runner_cfg.data['runner_credentials_dir']
    config_file = 'os/config'
    return os.path.join(config_dir, config_file)

def get_keystone_authtoken(**kwargs):
    '''
    :param kwargs: include auth_url, username, password, tenant_name, region_name
    :return: authentication token used by openstack clients
    '''
    # retrieve session authtoken (valid period?)
    try:
        return ksclient.Client(**kwargs).auth_token
    except KeyStoneExceptions.Unauthorized as e:
        return str(e)


def get_auth_credentials(profile, config_file=None):
    # get default config file if None provided
    if not config_file:
        config_file = get_config_file()

    # openstack ENV VAR to keystone Client argument mapping
    keystone_client_kwarg_map = {
        'OS_AUTH_URL': 'auth_url',
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_TENANT_NAME': 'tenant_name',
        'OS_REGION': 'region_name'
    }

    # extract openrc OS_* keys from map
    ocs_config_list = [attr for attr in keystone_client_kwarg_map]

    # parse openstack config file for indicated profile
    ocs_config = skybase.utils.parse_config_file(
        profile=profile,
        config_file=config_file,
        config_attrs=ocs_config_list)

    # return value from OS_* config using keystone map value as new key
    openstack_config = {keystone_client_kwarg_map[k]: v for k, v in ocs_config.items()}

    # acquire authtoken using configuration mapping
    authtoken = get_keystone_authtoken(**openstack_config)
    return authtoken


def get_cloud_conn(planet, config_file=None):
    # get default config file if None provided
    if not config_file:
        config_file = get_config_file()

    # acquire openstack credentials in form of auth token
    authtoken = get_auth_credentials(
        profile=planet.accountprofile,
        config_file=config_file)

    # copied in from slab project / compute / access & security / api access / Orchestration
    endpoint = planet.definition['api_endpoints']['orchestration']

    # establish Client connection for API version 1
    return heatclient.client.Client('1', endpoint=endpoint, token=authtoken)


def get_nova_conn(planet, config_file=None):
    # get default config file if None provided
    if not config_file:
        config_file = get_config_file()

    # TODO: unify with get_auth_credential adding type param. heat uses authtoken, nova uses actual cred values.
    # acquire nova authentication credentials

    keystone_client_kwarg_map = {
        'OS_AUTH_URL': 'auth_url',
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_TENANT_NAME': 'tenant_name',
        'OS_REGION': 'region_name'
    }

    # extract openrc OS_* keys from map
    ocs_config_list = [attr for attr in keystone_client_kwarg_map]

    ocs_config = skybase.utils.parse_config_file(
        profile=planet.accountprofile,
        config_file=config_file,
        config_attrs=ocs_config_list
    )

    return novaclient.client.Client('1.1', ocs_config['OS_USERNAME'], ocs_config['OS_PASSWORD'], ocs_config['OS_TENANT_NAME'], ocs_config['OS_AUTH_URL'])


def format_instance_info(server):
    result = dict()

    result[server.name] = {
        'name_tag': server.name,
        'instance_id': server.id,
        'instance_state': server.status,
        'instance_networks': server.networks,
    }
    return result

def format_instance_ip(server):
    result = dict()

    # TODO: review name_tag and it's relation to "server.name"
    # after change from plain list of IPs to a dict with name_tag and private_ip_address

    # extract one/many server networks ips and flatten into single list
    iplist = []
    for ips in server.networks.values():
        for ip in ips:
            iplist.append({
                'name_tag':server.name,
                'private_ip_address': str(ip)
            })
    # return dictionary with role name and ip list
    result[server.name] = iplist
    return result

def call_cloud_api(planet, stack_name, action, template_body=None, parameters=None):
    # acquire heat connection
    cloud_connection = get_cloud_conn(planet)

    # convert params from default list format to dict
    params_dict = {p[0]: p[1] for p in parameters} if parameters else dict()

    # TODO: rework into option switch format, execution action with lambda.  see skychef server/solo for examples.
    # cloud API actions
    result = dict()
    if action == 'create_stack':
        # call cloud API and return stack id
        api_response = cloud_connection.stacks.create(**{
            'stack_name': stack_name,
            'template': template_body,
            'parameters': params_dict,
        })
        result = api_response['stack']['id']

    elif action == 'describe_stacks':
        result = cloud_connection.resources.list(stack_name)

    elif action == 'delete_stack':
        result = cloud_connection.stacks.delete(stack_name)

    elif action == 'get_stack_status':
        stack = cloud_connection.stacks.get(stack_name)
        result = stack.stack_status

    elif action in ['get_instance_info', 'get_instance_ip']:
        # format handler options return different selections of instance info
        format_options = {
            'get_instance_info': format_instance_info,
            'get_instance_ip': format_instance_ip,
        }
        resources = cloud_connection.resources.list(stack_name)
        novaconn = get_nova_conn(planet)
        for resource in resources:
            if resource.resource_type == 'OS::Nova::Server':
                server = novaconn.servers.get(resource.physical_resource_id)
                result = format_options[action](server)
    return result


def upload_to_object_store(local_tar_src, profile, endpoint, container, path, archive_file):
    # create a temporary working directory
    with skybase.utils.make_temp_directory() as tdir:

        # create tar file in temporary directory
        target_file = os.path.join(tdir, archive_file)
        skybase.utils.make_tarfile(target_file, local_tar_src)

        # copy tar file to object storage
        result = local_to_object_store_copy(
            profile=profile,
            endpoint=endpoint,
            container=container,
            path='/'.join([path, archive_file]),
            local_file=target_file
        )

        return result


def get_object_store_conn(profile, endpoint):
    # acquire openstack credentials in form of auth token
    authtoken = get_auth_credentials(profile)

    # return swift API Connection
    return swiftclient.Connection(preauthtoken=authtoken, preauthurl=endpoint, retries=10)


def local_to_object_store_copy(profile, endpoint, container, path, local_file, retries=2):
    # acquire swift API Connection
    swiftconn = get_object_store_conn(profile, endpoint)

    # initialize response object
    result ={
        'container': container,
        'path': path,
    }

    # copy local file to swift object store
    with open(local_file, 'r') as swift_file:
        # attempt to upload to object store to maximum retries
        for attempt in range(retries):
            try:
                result['hash'] = swiftconn.put_object(
                    container=container,
                    obj=path,
                    contents=swift_file)
            except httplib.BadStatusLine:
                # pass through this error while less than max retries
                pass
            else:
                # successful upload! break from remaining retry attempts
                break
        else:
            # all upload attempts failed for BadStatusLine -- reraise.
            raise httplib.BadStatusLine

    return result

def list_objects(profile, endpoint, container, prefix):
    # acquire swift API Connection
    swiftconn = get_object_store_conn(profile, endpoint)

    # list container/prefix results
    list_result=swiftconn.get_container(
        container=container,
        prefix=prefix,
    )

    # return only prefix/filename results
    keylist = [key['name'] for key in list_result[1]]
    return keylist

def delete_objects(profile, endpoint, container, prefix,):
    # acquire swift API Connection
    swiftconn = get_object_store_conn(profile, endpoint)

    # get list of container/prefix/filename  keys
    keylist = list_objects(profile, endpoint, container, prefix)

    # initialize results
    result = dict()

    # attempt to delete each object key
    for key in keylist:
        try:
            result[key] = swiftconn.delete_object(container, key)
        except swiftclient.exceptions.ClientException as e:
            result[key] = skybase.utils.simple_error_format(e)

    return result

def preprocess_userdata(template):
    # apply transformations to userdata template and return as list of lines
    userdata_as_list = []
    for line in template.split('\n'):
        userdata_as_list.append(r'"{0}",'.format(line))
    return userdata_as_list


def are_stacks_valid(stacks):
    if stacks:
        valid_stacks = ['ERROR:' not in v for v in stacks.values()]
        return bool(reduce(lambda x, y: x*y, valid_stacks))

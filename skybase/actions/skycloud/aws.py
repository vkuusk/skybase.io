import os

import boto.cloudformation
import boto.ec2
import boto.ec2.autoscale
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from skybase import config as sky_cfg
import skybase.utils

def get_config_file(config_dir=None):
    if not config_dir:
        runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)
        config_dir = runner_cfg.data['runner_credentials_dir']
    config_file = 'aws/config'
    return os.path.join(config_dir, config_file)


def get_auth_credentials(profile='default', config_file=None):
    if not config_file:
        config_file = get_config_file()

    # parse aws config file
    aws_config = skybase.utils.parse_config_file(
        profile=profile,
        config_file=config_file,
        config_attrs=['aws_access_key_id', 'aws_secret_access_key'])

    # return access and secret keys
    return aws_config['aws_access_key_id'], aws_config['aws_secret_access_key']


def get_cloud_conn(planet, config_file=None):
    if not config_file:
        config_file = get_config_file()

    # provide connection to AWS CFN services
    aws_key, aws_secret = get_auth_credentials(
        profile=planet.accountprofile,
        config_file=config_file)

    # attempt to connect to CFN region
    return boto.cloudformation.connect_to_region(
        planet.region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret)

def get_asg_conn(planet, config_file=None):
    # provide connection to AWS CFN services
    aws_key, aws_secret = get_auth_credentials(
        profile=planet.accountprofile,
        config_file=config_file)

    # attempt to connect to CFN region
    return boto.ec2.autoscale.connect_to_region(
        region_name=planet.region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret)

def get_ec2_conn(planet, config_file=None):
    # provide connection to AWS CFN services
    aws_key, aws_secret = get_auth_credentials(
        profile=planet.accountprofile,
        config_file=config_file)

    # attempt to connect to CFN region
    return boto.ec2.connect_to_region(
        planet.region,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret)

def get_info(physical_resource_id_list, planet, format_handler):
    conn_ec2 = get_ec2_conn(planet)
    instances = conn_ec2.get_only_instances(physical_resource_id_list) if physical_resource_id_list else []
    info = format_handler(instances)
    return info

def get_asg_info(physical_resource_id, planet, format_handler):
    conn_asg = get_asg_conn(planet)
    asg = conn_asg.get_all_groups(names=[physical_resource_id])[0]
    asg_instance_ids = [i.instance_id for i in asg.instances]
    info = get_info(asg_instance_ids, planet, format_handler)
    return info

def get_ec2_info(instance, planet, format_handler):
    info = get_info([instance], planet, format_handler)
    return info

def format_instance_info(instances):
    result = dict()
    for instance in instances:
        instance_name = instance.tags.get('Name')
        if not instance_name in result:
            result[instance_name] = []
        result[instance_name].append({
            'name_tag': instance_name,
            'instance_id': instance.id,
            'private_ip_address': instance.private_ip_address,
            'instance_state': instance.state,
            })
    return result

def format_instance_ip(instances):
    result = dict()
    for instance in instances:
        instance_name = instance.tags.get('Name')
        if not instance_name in result:
            result[instance_name] = []
        result[instance_name].append({
            'name_tag': instance_name,
            'private_ip_address': instance.private_ip_address
        })
    return result

def call_cloud_api(planet, stack_name, action, template_body=None, parameters=[]):
    # acquire cloudformation connection to region
    cloud_connection = get_cloud_conn(planet)

    # TODO: rework into option switch format, execution action with lambda.  see skychef server/solo for examples.
    # perform action on AWS
    if action == 'create_stack':
        return cloud_connection.create_stack(
            stack_name=stack_name,
            template_body=template_body,
            capabilities=['CAPABILITY_IAM'],
            parameters=parameters,
        )
    elif action == 'describe_stacks':
        return cloud_connection.describe_stacks(
            stack_name_or_id=stack_name
        )
    elif action == 'delete_stack':
        return cloud_connection.delete_stack(
            stack_name_or_id=stack_name
        )
    elif action == 'get_stack_status':
        stack, = call_cloud_api (
            planet=planet,
            stack_name=stack_name,
            action='describe_stacks')
        return stack.stack_status
    elif action in ['get_instance_info', 'get_instance_ip']:
        # format handler options return different selections of instance info
        format_options = {
            'get_instance_info': format_instance_info,
            'get_instance_ip': format_instance_ip,
        }

        # acquire stack object
        stack_desc = cloud_connection.describe_stacks(stack_name_or_id=stack_name)
        for stack in stack_desc:
            info = {}
            # query resources for autoscaling and ec2 types
            for resource in stack.describe_resources():
                if resource.resource_type == 'AWS::AutoScaling::AutoScalingGroup':
                    info.update(get_asg_info(resource.physical_resource_id, planet, format_options[action]))
                elif resource.resource_type == 'AWS::EC2::Instance':
                    info.update(get_ec2_info(resource.physical_resource_id, planet, format_options[action]))
            return info


def upload_to_object_store(local_tar_src, profile, bucket_name, key_path, archive_file):
    # create a temporary working directory
    with skybase.utils.make_temp_directory() as tdir:

        # create tar file in temporary directory
        target_file = os.path.join(tdir, archive_file)
        skybase.utils.make_tarfile(target_file, local_tar_src)

        # copy tar file to object storage
        result = local_to_object_store_copy(
            profile=profile,
            bucket_name=bucket_name,
            key_path='/'.join([key_path, archive_file]),
            local_file=target_file
        )

        return result


def get_object_store_conn(profile):
    aws_key, aws_secret = get_auth_credentials(profile)
    return S3Connection(aws_key, aws_secret)


def local_to_object_store_copy(profile, bucket_name, key_path, local_file):
    # acquire s3 connection and bucket
    s3conn = get_object_store_conn(profile)
    bucket = s3conn.get_bucket(bucket_name)

    # create s3 Key and copy contents from local file
    s3key = Key(bucket, key_path)
    s3key.set_contents_from_filename(local_file)

    result = {
        'bucket': bucket.name,
        'key': s3key.name,
        'etag': s3key.etag,

    }
    return result


def list_objects(profile, bucket_name, key_path):
    s3conn = get_object_store_conn(profile)
    bucket = s3conn.get_bucket(bucket_name)
    bucketListResultSet = bucket.list(prefix=key_path)
    keylist = [key.name for key in bucketListResultSet]
    return keylist


def delete_objects(profile, bucket_name, key_path):
    s3conn = get_object_store_conn(profile)
    bucket = s3conn.get_bucket(bucket_name)
    keylist = list_objects(profile, bucket_name, key_path)
    delete_result = bucket.delete_keys(keylist)
    result = {
        'deleted': [deleted.key for deleted in delete_result.deleted],
        'errors': [(error.key, error.message) for error in delete_result.errors],
    }
    return result


def preprocess_userdata(template):
    # apply transformations to userdata template and return as list of lines
    userdata_as_list = []
    for line in template.split('\n'):
        userdata_as_list.append(r'"{0}",'.format(line))
    return userdata_as_list


def are_stacks_valid(stacks):
    if stacks:
        # TODO: test for first False value; default to True ???
        valid_stacks = ['BotoServerError' not in v for v in stacks.values()]
        return bool(reduce(lambda x, y: x*y, valid_stacks))

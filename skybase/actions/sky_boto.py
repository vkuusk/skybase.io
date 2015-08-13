# This file is heavily based the SALTSTACK's boto module(s)
# https://github.com/saltstack/salt/blob/develop/salt/modules/boto_cfn.py
# mostly removed error checking and flexibility
# !!! REVISIT AFTER INTEGRATION WITH SALT

import sys
import boto
import os
#####
# CloudFormation
import boto.cloudformation
import boto.cloudformation.connection
import boto.cloudformation.stack
import boto.cloudformation.template
######
# S3
import boto.s3
import boto.s3.connection
import boto.s3.bucket
from boto.s3.key import Key




#######################################################
# CloudFormation portion of the Functions
def stack_exists(name, region, access_key=None, secret_key=None):
    '''
    Check to see if a stack exists.
    CLI example::
        salt myminion boto_cfn.exists mystack region=us-east-1
    '''
    conn = _get_cfn_connection(region, access_key, secret_key)
    if not conn:
        return False
    try:
        stack = conn.describe_stacks(name)
    except boto.exception.BotoServerError as e:
        return False
    return True








# ------------
def _get_cfn_connection(region, access_key=None, secret_key=None):
    # region is required - no default region
    # if keys do not exist boto will use IAM profile. right?
    try:
        conn = boto.cloudformation.connect_to_region(region,
                                                     aws_access_key_id=access_key,
                                                     aws_secret_access_key=secret_key)
    except boto.exception.NoAuthHandlerFound:
        #log.error('No authentication credentials found when attempting to'
        #          ' make boto cfn connection.')
        return None
    return conn


#########################################################
# S3 portion

def _get_s3_connection(access_key=None, secret_key=None):

    try:
        conn = boto.s3.connection.S3Connection(access_key, secret_key)
    except boto.exception.NoAuthHandlerFound:
        return None

    return conn


def upload_to_s3(bucket_name, file_path, logger, prefix=None, access_key=None, secret_key=None, dry_run=False):
    valid = True
    result_string = ""
    s3_conn = _get_s3_connection(access_key, secret_key)
    if s3_conn.lookup(bucket_name):
        s3_key = Key(s3_conn.get_bucket(bucket_name))
        if prefix:
            s3_key.key = os.path.join(prefix, os.path.basename(file_path))
        else:
            s3_key.key = os.path.basename(file_path)

        def percent_cb(complete, total):
            if total is not 0:
                percentage = int(complete) * 100 / int(total);
                logger.write('Uploading to S3: ' + str(complete) + ' / ' + str(total) + ' ( ' + str(percentage) + '%)',
                             multi_line=False)
            else:
                sys.stdout.write('.')
            sys.stdout.flush()

        if dry_run:
            result_string += 'Skipping actual upload to S3 due to dry run.\n'
        else:
            s3_key.set_contents_from_filename(file_path, cb=percent_cb, num_cb=5)
            result_string += 'Uploaded package from ' + file_path + ' to S3 bucket ' + bucket_name + '\n'
    else:
        result_string += "Cannot find S3 bucket with name " + bucket_name + '\n'
        valid = False

    return {"valid": valid, "result_string": result_string}


def download_from_s3(bucket_name, file_name, dest_path, logger, prefix=None, access_key=None, secret_key=None, dry_run=False):
    valid = True
    result_string = ""
    s3_conn = _get_s3_connection(access_key, secret_key)
    if s3_conn.lookup(bucket_name):
        bucket = s3_conn.get_bucket(bucket_name)
        files = bucket.list(prefix=prefix)
        for f in files:
            if prefix:
                k = os.path.join(prefix, file_name)
            else:
                k = file_name
            if k == str(f.key):
                def percent_cb(complete, total):
                    percentage = int(complete) * 100 / int(total)
                    logger.write('Downloading from S3: ' + str(complete) + ' / ' + str(total)
                                 + ' ( ' + str(percentage) + '%)', multi_line=False)
                    sys.stdout.flush()
                if dry_run:
                    result_string += 'Skipping actual download from S3 due to dry run.\n'
                else:
                    if not f.get_contents_to_filename(os.path.join(dest_path, file_name), cb=percent_cb, num_cb=5):
                        result_string += 'Downloaded package to ' + os.path.join(dest_path, file_name) + \
                                         ' from S3 bucket ' + bucket_name + '\n'
                        return {"valid": valid, "result_string": result_string}

        result_string += file_name + " does not exist in S3 bucket " + bucket_name + '\n'
        valid = False
    else:
        result_string += "Cannot find S3 bucket with name " + bucket_name + '\n'
        valid = False
    return {"valid": valid, "result_string": result_string}


def delete_from_s3(bucket_name, file_name, prefix=None, access_key=None, secret_key=None, dry_run=False):
    valid = True
    result_string = ""
    s3_conn = _get_s3_connection(access_key, secret_key)
    if s3_conn.lookup(bucket_name):
        bucket = s3_conn.get_bucket(bucket_name)
        k = Key(bucket)
        if prefix:
            k.key = os.path.join(prefix, file_name)
        else:
            k.key = file_name
        if dry_run:
            result_string += 'Skipping actual delete from S3 due to dry run.\n'
        else:
            bucket.delete_key(k)
            result_string += "Deleted file " + file_name + " from S3 bucket " + bucket_name + '\n'
    else:
        result_string += "Cannot find S3 bucket with name " + bucket_name + "\n"
        valid = False
    return {"valid": valid, "result_string": result_string}


def copy_object_s3(src_bucket_name, dst_bucket_name, file_name, src_prefix=None, dst_prefix=None,
                   access_key=None, secret_key=None, dry_run=False):
    valid = True
    result_string = ""
    s3_conn = _get_s3_connection(access_key, secret_key)
    if s3_conn.lookup(src_bucket_name):
        bucket = s3_conn.get_bucket(src_bucket_name)
        if src_prefix:
            src_key = os.path.join(src_prefix, file_name)
        else:
            src_key = file_name
        key = bucket.lookup(src_key)
        if s3_conn.lookup(dst_bucket_name):
            if dry_run:
                result_string += 'Skipping actual file move in S3 due to dry run.\n'
            else:
                if dst_prefix:
                    dst_key = os.path.join(dst_prefix, file_name)
                else:
                    dst_key = file_name
                key.copy(dst_bucket_name, dst_key, metadata=None, preserve_acl=True)
                src_prefix = '' if src_prefix is None else src_prefix
                dst_prefix = '' if dst_prefix is None else dst_prefix
                result_string += "Copied file " + file_name + " from /" + src_prefix + " in S3 bucket " \
                                 + src_bucket_name + " to /" + dst_prefix + " in S3 bucket " + dst_bucket_name + '\n'
        else:
            result_string += "Cannot find destination S3 bucket with name " + dst_bucket_name + "\n"
            valid = False
    else:
        result_string += "Cannot find source S3 bucket with name " + src_bucket_name + "\n"
        valid = False

    return {"valid": valid, "result_string": result_string}


def move_object_s3(src_bucket_name, dst_bucket_name, file_name, src_prefix=None, dst_prefix=None,
                   access_key=None, secret_key=None, dry_run=False):
    valid = True
    result_string = ""
    copy_result = copy_object_s3(src_bucket_name, dst_bucket_name, file_name, src_prefix=src_prefix,
                                 dst_prefix=dst_prefix, access_key=access_key, secret_key=secret_key, dry_run=dry_run)
    result_string += copy_result["result_string"]
    if not copy_result["valid"]:
        valid = False
    delete_result = delete_from_s3(src_bucket_name, file_name, prefix=src_prefix, access_key=access_key,
                                   secret_key=secret_key, dry_run=dry_run)
    result_string += delete_result["result_string"]
    if not delete_result["valid"]:
        valid = False
    return {"valid": valid, "result_string": result_string}
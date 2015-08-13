import os
import shutil

from boto.s3.key import Key
from boto.s3.connection import S3Connection

import skybase.actions.skycloud.aws as aws
from skybase.utils import extract_tar_file


def artiball_transfer(artiball_key, bucket_name, profile, release_dir, s3_path=''):

    result = dict()

    result['args'] = {
        'artiball_key': artiball_key,
        'bucket_name': bucket_name,
        'profile': profile,
        'release_dir': release_dir,
        's3_path': s3_path
    }

    aws_key, aws_secret = aws.get_auth_credentials(profile)
    conn = S3Connection(aws_key, aws_secret)
    bucket = conn.get_bucket(bucket_name)
    source_file = artiball_key + '.tar.gz'
    artiball = Key(bucket, '/'.join([s3_path, source_file]))

    result['source'] = {
        'bucket': str(bucket),
        'source_file': source_file,
        'artiball': str(artiball),
    }

    if artiball:
        target_dir = os.path.join(release_dir, artiball_key)
        target_file = os.path.join(release_dir, source_file)
        result['target'] = {
            'target_dir': target_dir,
            'target_file': target_file,
        }

        # download artiball tarfile into local target_file
        artiball.get_contents_to_filename(target_file)

        # remove previous release if exists
        try:
            shutil.rmtree(target_dir)
        except OSError:
            pass

        # create new target directory for release
        os.mkdir(target_dir)

        # extract tar file contents into release directory
        extract_tar_file(target_dir=target_dir, tar_file=target_file)

        # cleanup release dir of tar files
        os.remove(target_file)

    return result

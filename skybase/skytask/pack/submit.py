import os
import logging
import tarfile
import shutil
import ConfigParser
import tempfile

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.actions import pack as pack_actions
from skybase.skytask import pack
from skybase.actions import sky_boto as sky_boto_actions
from skybase.utils.logger import Logger


def pack_submit_add_arguments(parser):

    parser.add_argument(
        '-d',
        '--directory',
        dest='base_dir',
        action='store'
    )
    parser.add_argument(
        '-a',
        '--artiball',
        dest='artiball',
        action='store',
        default=None
    )
    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default local)'
    )


class Submit(SkyTask):
    def __init__(self, all_args, runner_cfg):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'pack.submit'
        self.args = all_args
        self.runner_cfg = runner_cfg
        self.aws_access_key_id = None
        self.aws_secret_access_key = None

        if self.args['base_dir']:
            self.base_dir = self.args['base_dir']
            if self.base_dir.split('/')[-1] is not 'skybase':
                self.base_dir = os.path.join(self.base_dir, 'skybase')
        else:
            self.tdir = tempfile.mkdtemp()
            self.base_dir = os.path.join(self.tdir, 'skybase')
        self.tmp_dir = os.path.join(self.base_dir, 'tmp')
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

    def execute(self):
        aws_creds_profile = self.runner_cfg.data['package_depot_aws_profile']
        aws_creds_file = os.path.join(self.runner_cfg.data['runner_credentials_dir'], 'aws', 'config')
        if os.path.exists(aws_creds_file):
            config = ConfigParser.ConfigParser()
            config.read([str(aws_creds_file)])
            self.aws_access_key_id = config.get('profile ' + aws_creds_profile, 'aws_access_key_id')
            self.aws_secret_access_key = config.get('profile ' + aws_creds_profile, 'aws_secret_access_key')

            if self.args['artiball'].endswith('.tar.gz'):
                artiball = self.args['artiball']
            else:
                artiball = self.args['artiball'] + '.tar.gz'

            pack.set_incoming_s3_bucket()
            self.logger.write('Downloading package from S3 bucket ' + pack.PACKAGE_INCOMING_S3_BUCKET, multi_line=False)
            download_result = sky_boto_actions.download_from_s3(pack.PACKAGE_INCOMING_S3_BUCKET, artiball,
                                                                self.tmp_dir, self.logger,
                                                                access_key=self.aws_access_key_id,
                                                                secret_key=self.aws_secret_access_key,
                                                                dry_run=False)
            self.result.output += download_result["result_string"]
            if not download_result["valid"]:
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result

            artiball_file = tarfile.open(os.path.join(self.tmp_dir, artiball), 'r:gz')
            artiball_dir = os.path.join(self.tmp_dir, artiball.split('.tar.gz')[0])
            artiball_file.extractall(os.path.join(artiball_dir, 'skybase'))
            self.logger.write('Validating package in ' + artiball_dir, multi_line=False)
            validate_result = pack_actions.validate_with_schema(artiball_dir, 'artiball',
                                                                update_content_from_config=False)
            if validate_result["valid"]:
                self.result.output += "All content validated, ready for pack submit.\n"
            else:
                self.result.output += "Invalid content for submission, please verify artiball is valid.\n"
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result

            app_dir = os.path.join(artiball_dir, 'skybase', 'app')
            yum_aws_creds_file = os.path.join(self.runner_cfg.data['runner_credentials_dir'], 'aws', 'config')

            if os.path.exists(yum_aws_creds_file):
                config = ConfigParser.ConfigParser()
                config.read([str(yum_aws_creds_file)])
                yum_replications = self.runner_cfg.data['yum_replication']
                for yum_replication in yum_replications:
                    yum_aws_creds_profile = yum_replication['profile']
                    yum_aws_access_key_id = config.get('profile ' + yum_aws_creds_profile, 'aws_access_key_id')
                    yum_aws_secret_access_key = config.get('profile ' + yum_aws_creds_profile, 'aws_secret_access_key')
                    for f in os.listdir(app_dir):
                        if os.path.splitext(f)[1] == '.rpm':
                            # Hardcoding default to True for pack group command, revisit later
                            self.args['apply'] = True
                            if self.args['apply']:
                                upload_result = sky_boto_actions.upload_to_s3(yum_replication['name'],
                                                                              os.path.join(app_dir, f),
                                                                              self.logger, prefix='inbox/skybase',
                                                                              access_key=yum_aws_access_key_id,
                                                                              secret_key=yum_aws_secret_access_key,
                                                                              dry_run=False)
                            else:
                                upload_result = sky_boto_actions.upload_to_s3(yum_replication['name'],
                                                                              os.path.join(app_dir, f),
                                                                              self.logger, prefix='inbox/skybase',
                                                                              access_key=yum_aws_access_key_id,
                                                                              secret_key=yum_aws_secret_access_key,
                                                                              dry_run=True)
                            self.result.output += upload_result["result_string"]
                            if not upload_result["valid"]:
                                self.result.status = sky_cfg.API_STATUS_FAIL
                                return self.result

            else:
                self.result.output += "Cannot locate aws credentials, please confirm they are set in " \
                                      + yum_aws_creds_file + "\n"
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result
        else:
            self.result.output += "Cannot locate aws credentials, please confirm they are set in " + aws_creds_file \
                                  + "\n"
            self.result.status = sky_cfg.API_STATUS_FAIL
            return self.result

        file_path = os.path.join(self.tmp_dir, artiball)
        depot_bucket_name = os.path.expanduser(self.runner_cfg.data['package_depot_S3_bucket'])

        # Hardcoding default to True for pack group command, revisit later
        self.args['apply'] = True
        if self.args['apply']:
            self.logger.write('Uploading package to S3 bucket ' + depot_bucket_name, multi_line=False)
            upload_result = sky_boto_actions.upload_to_s3(depot_bucket_name, file_path, self.logger,
                                                          access_key=self.aws_access_key_id,
                                                          secret_key=self.aws_secret_access_key,
                                                          dry_run=False)
            self.result.output += upload_result["result_string"]
            if not upload_result["valid"]:
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result

            self.logger.write('Archiving package in S3 bucket ' + pack.PACKAGE_INCOMING_S3_BUCKET, multi_line=False)
            move_result = sky_boto_actions.move_object_s3(pack.PACKAGE_INCOMING_S3_BUCKET, pack.PACKAGE_INCOMING_S3_BUCKET,
                                                          os.path.basename(file_path),
                                                          src_prefix=None, dst_prefix='archive',
                                                          access_key=self.aws_access_key_id,
                                                          secret_key=self.aws_secret_access_key,
                                                          dry_run=False)
        else:
            self.logger.write('DRY RUN :::: Dry running steps for package upload to S3 bucket ' + depot_bucket_name,
                              multi_line=False)
            upload_result = sky_boto_actions.upload_to_s3(depot_bucket_name, file_path, self.logger,
                                                          access_key=self.aws_access_key_id,
                                                          secret_key=self.aws_secret_access_key,
                                                          dry_run=True)
            self.result.output += upload_result["result_string"]
            if not upload_result["valid"]:
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result
            self.logger.write('DRY RUN :::: Dry running steps for archiving package in S3 bucket '
                              + pack.PACKAGE_INCOMING_S3_BUCKET, multi_line=False)
            move_result = sky_boto_actions.move_object_s3(pack.PACKAGE_INCOMING_S3_BUCKET, pack.PACKAGE_INCOMING_S3_BUCKET,
                                                          os.path.basename(file_path),
                                                          src_prefix=None, dst_prefix='archive',
                                                          access_key=self.aws_access_key_id,
                                                          secret_key=self.aws_secret_access_key,
                                                          dry_run=True)
        self.result.output += move_result["result_string"]
        if not move_result["valid"]:
                self.result.status = sky_cfg.API_STATUS_FAIL
                return self.result

        if hasattr(self,'tdir') and os.path.exists(self.tdir):
            shutil.rmtree(self.tdir)
        else:
            shutil.rmtree(self.tmp_dir)
        self.result.status = sky_cfg.API_STATUS_SUCCESS
        return self.result

    def preflight_check(self):
        result = skytask.TaskResult()
        if self.args['artiball'] is None:
            result.output += "Missing artiball argument, please use -a to specify.\n"
            shutil.rmtree(self.tmp_dir)
            result.status = 'FAIL'
        return result
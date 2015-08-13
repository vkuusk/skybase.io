import os
import logging
import ConfigParser

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.skytask import pack
from skybase.actions import sky_boto as sky_boto_actions
from skybase.utils.logger import Logger


def pack_upload_add_arguments(parser):

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
        choices={'local'},
        default='local',
        help='execution mode (default local)'
    )


class Upload(SkyTask):
    def __init__(self, all_args, runner_cfg):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'pack.upload'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):
        if self.args['base_dir']:
            base_dir = self.args['base_dir']
            if base_dir.split('/')[-1] is not 'skybase':
                base_dir = os.path.join(base_dir, 'skybase')
        else:
            base_dir = os.path.join(os.getcwd(), 'skybase')

        pack.set_incoming_s3_bucket()

        if self.args['artiball']:
            if self.args['artiball'].endswith('.tar.gz'):
                file_path = os.path.join(base_dir, 'package', self.args['artiball'])
            else:
                file_path = os.path.join(base_dir, 'package', self.args['artiball'] + '.tar.gz')
        else:
            packages = os.listdir(os.path.join(base_dir, 'package'))
            for package in packages:
                file_path = os.path.join(base_dir, 'package', package)

        aws_creds_file = os.path.expanduser(os.path.join('~', '.aws', 'config'))
        if os.path.exists(aws_creds_file):
            config = ConfigParser.ConfigParser()
            config.read([str(aws_creds_file)])
            aws_access_key_id = config.get('default', 'aws_access_key_id')
            aws_secret_access_key = config.get('default', 'aws_secret_access_key')

            # Hardcoding default to True for pack group command, revisit later
            self.args['apply'] = True
            if self.args['apply']:
                self.logger.write('Uploading package to S3 bucket ' + pack.PACKAGE_INCOMING_S3_BUCKET, multi_line=False)
                upload_result = sky_boto_actions.upload_to_s3(pack.PACKAGE_INCOMING_S3_BUCKET, file_path, self.logger,
                                                              access_key=aws_access_key_id,
                                                              secret_key=aws_secret_access_key,
                                                              dry_run=False)
            else:
                self.logger.write('DRY RUN :::: Dry running steps for package upload to S3 bucket '
                                  + pack.PACKAGE_INCOMING_S3_BUCKET, multi_line=False)
                upload_result = sky_boto_actions.upload_to_s3(pack.PACKAGE_INCOMING_S3_BUCKET, file_path, self.logger,
                                                              access_key=aws_access_key_id,
                                                              secret_key=aws_secret_access_key,
                                                              dry_run=True)

            if upload_result["valid"]:
                self.result.status = sky_cfg.API_STATUS_SUCCESS
            else:
                self.result.status = sky_cfg.API_STATUS_FAIL
            self.result.output += upload_result["result_string"]
        else:
            self.result.output += "Cannot locate aws credentials, please confirm they are set in " + aws_creds_file \
                                  + "\n"
            self.result.status = sky_cfg.API_STATUS_FAIL
            return self.result

        return self.result

    def preflight_check(self):
        result = skytask.TaskResult()
        if self.args['base_dir']:
            base_dir = self.args['base_dir']
            if base_dir.split('/')[-1] is not 'skybase':
                base_dir = os.path.join(base_dir, 'skybase')
        else:
            base_dir = os.path.join(os.getcwd(), 'skybase')

        if self.args['artiball']:
            if self.args['artiball'].endswith('.tar.gz'):
                file_path = os.path.join(base_dir, 'package', self.args['artiball'])
            else:
                file_path = os.path.join(base_dir, 'package', self.args['artiball'] + '.tar.gz')
            if not os.path.exists(file_path):
                result.output += "Cannot find specified artiball " + file_path + "\n"
                result.status = 'FAIL'
                return result
        else:
            packages = os.listdir(os.path.join(base_dir, 'package'))
            if len(packages) > 1:
                result.output += "Multiple artiballs found in project, please use -a to specify artiball.\n"
                result.status = 'FAIL'
                return result
            for package in packages:
                if package.endswith('.tar.gz'):
                    result.status = sky_cfg.API_STATUS_SUCCESS
                    return result
            result.output += "Cannot find package in project, please use -a to specify artiball.\n"
            result.status = 'FAIL'
        return result
import logging

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger

from skybase.utils import schema as utils

from os.path import expanduser
import os



def configure_user_credentials_add_arguments(parser):

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local'},
        default='local',
        help='execution mode (at this time only LOCAL is allowed for this command)'
    )

    parser.add_argument(
        '-u', '--userid',
        dest='user_id',
        action='store',
        help='User ID '
    )

    parser.add_argument(
        '-k', '--key',
        dest='secret_key',
        action='store',
        help='Secret_Key assigned to User'
    )
    parser.add_argument(
        '-f', '--force',
        dest='force',
        action='store_true',
        default=False,
        help='Overwrite credentials'
    )



class UserCredentials(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        # TODO: Note that we can read the runner config just right here, then it will solve problem of reading config
        # dir before calling the task.

        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'configure.user_credentials'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def preflight_check(self):
        # initialize results container
        preflight_result = []

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result

    def execute(self):

        # TODO: create standard result object (from MTW)
        result_dict = dict(
            # TODO: define the standard structure for e result
            # data=dict(),
            # the following works for local mode and raw format
            data='',
            type=skytask.output_format_raw,
            status=None
        )

        user_id = self.args['user_id']
        secret_key = self.args['secret_key']
        # TODO: For consistency, change the name from "key" to "secret_key" inside credentials file
        new_creds = {'user_id': user_id, 'key': secret_key}

        # verify that ~/.skybase dir exists
        home_dir = expanduser("~")
        skybase_user_dir = os.path.join(home_dir,'.skybase')
        if not os.path.isdir(skybase_user_dir):
            os.mkdir(skybase_user_dir)

        creds_file = os.path.join(skybase_user_dir,'credentials.yaml')

        if (not os.path.exists(creds_file)) or self.args['force'] :
            utils.write_dict_to_yaml_file(new_creds, creds_file)
            result_dict['data'] += 'Credentials are written to ' + skybase_user_dir
        else:
            result_dict['data'] += '\nFile Exists: ' + creds_file + '\n' +'\nUse "--force" option\n'
            old_creds = utils.read_yaml_from_file(creds_file)

        # TODO: result.status will be derived from all action status values.(from MTW)
        self.result.status = sky_cfg.API_STATUS_SUCCESS
        self.result.output = result_dict['data']

        return self.result


import logging
import sqlite3

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger
from skybase.actions.auth.db import delete_user, unique_user_exists
from skybase.exceptions import SkyBaseUserAuthorizationError
from skybase.utils import simple_error_format
import skybase.exceptions

def user_delete_add_arguments(parser):
    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )

    parser.add_argument(
        '-u', '--username',
        dest='username',
        action='store',
        default='',
        required=True,
        help='unique username'
    )


class Delete(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'user.delete'
        self.args = all_args
        self.runner_cfg = runner_cfg

        self.apply = self.args.get('apply')
        self.username = self.args.get('username')


    def preflight_check(self):
        # initialize results container
        preflight_result = []
        if not unique_user_exists(self.username):
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(simple_error_format(
                SkyBaseUserAuthorizationError(
                    'cannot find username: {0}'.format(self.username))))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):
        """
        delete one user record
        """
        self.result.format = skytask.output_format_raw

        if self.apply:
            try:
                # attempt to delete record using username
                delete_user(self.username)

                if not unique_user_exists(self.username):
                    self.result.status = sky_cfg.API_STATUS_SUCCESS
                    self.result.output = 'user record deleted: {0}'.format(self.username)
                else:
                    self.result.status = sky_cfg.API_STATUS_FAIL
                    self.result.output = 'delete attempt failed user: {0}'.format(self.username)

            except (skybase.exceptions.SkyBaseError, sqlite3.Error) as e:
                self.result.output = simple_error_format(e)
                self.result.status = sky_cfg.API_STATUS_FAIL

        else:
            self.result.status = sky_cfg.API_STATUS_SUCCESS
            self.result.output = 'user record to be deleted: {0}; --apply required'.format(self.username)

        return self.result




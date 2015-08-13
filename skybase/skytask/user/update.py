import logging
import sqlite3

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger
import skybase.auth.schema
from skybase.actions.auth.db import update_email, upsert_userroles, unique_user_exists, find_user
from skybase.exceptions import SkyBaseUserAuthorizationError
from skybase.utils import simple_error_format


def user_update_add_arguments(parser):
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

    parser.add_argument(
        '-r', '--role',
        dest='role',
        action='store',
        choices=skybase.auth.schema.ROLES,
        help='update user role'
    )

    parser.add_argument(
        '-e', '--email',
        dest='email',
        action='store',
        help='update user email'
    )


class Update(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'user.update'
        self.args = all_args
        self.runner_cfg = runner_cfg

        self.apply = self.args.get('apply')
        self.username = self.args.get('username')
        self.role = self.args.get('role')
        self.email = self.args.get('email')


    def preflight_check(self):
        # initialize results container
        preflight_result = []

        # validate that username exists
        if not unique_user_exists(self.username):
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(simple_error_format(
                SkyBaseUserAuthorizationError(
                    'cannot find username: {0}'.format(self.username))))

        # require at least something to update
        if self.role is None and self.email is None:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append('choose at least one update option: --role, --email')

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):

        """
        update user email and/or role
        """
        self.result.format = skytask.output_format_json

        if self.apply:
            try:
                # attempt to update user information
                if self.email:
                    update_email(self.username, self.email)
                if self.role:
                    upsert_userroles(self.username, self.role)

                self.result.status = sky_cfg.API_STATUS_SUCCESS
                self.result.output = 'user updated: {0}'.format(find_user(self.username)[0])

            except (skybase.exceptions.SkyBaseError, sqlite3.Error) as e:
                self.result.output = simple_error_format(e)
                self.result.status = sky_cfg.API_STATUS_FAIL

        else:
            self.result.status = sky_cfg.API_STATUS_SUCCESS
            self.result.output = 'user not updated: {0}; --apply required'.format(find_user(self.username)[0])

        return self.result




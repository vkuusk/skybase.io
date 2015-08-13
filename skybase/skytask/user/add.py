import logging
import sqlite3

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger
import skybase.auth.schema
from skybase.actions.user import generate_random_key
from skybase.actions.auth.db import find_user, create_user, unique_user_exists
from skybase.exceptions import SkyBaseUserIdNotFoundError, \
    SkyBaseUserAuthorizationError
from skybase.utils import simple_error_format


def user_add_add_arguments(parser):
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
        default=skybase.auth.schema.ROLES_DEFAULT,
        help='role (default to {0})'.format(skybase.auth.schema.ROLES_DEFAULT)
    )

    parser.add_argument(
        '-e', '--email',
        dest='email',
        action='store',
        help='email for user'
    )

    parser.add_argument(
        '-s', '--secret',
        dest='secret',
        action='store',
        help='authentication secret for user'
    )


class Add(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'user.add'
        self.args = all_args
        self.runner_cfg = runner_cfg

        self.apply = self.args.get('apply')
        self.username = self.args.get('username')
        self.role = self.args.get('role')
        self.email = self.args.get('email')
        self.secret = self.args.get('secret')

    def preflight_check(self):
        # initialize results container
        preflight_result = []

        # validate that username doesn't exist
        if unique_user_exists(self.username):
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(simple_error_format(
                SkyBaseUserAuthorizationError(
                    'username {0} exists'.format(self.username))))

        if not self.secret:
            # if secret not defined, generate a secret key
            self.secret = generate_random_key()

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):

        """
        give the user name and role, create password and create a record in dbauth, return username, password, role
        """
        self.result.format = skytask.output_format_json

        if self.apply:
            try:
                # attempt to new user records from options
                create_user(self.username, self.secret, self.email, self.role)

                # attempt to read newly created record
                user_record = find_user(self.username)[0]

                # check for non-empty list of records; find_user() returns single/unique
                if user_record:
                    self.result.status = sky_cfg.API_STATUS_SUCCESS
                    self.result.output = 'user added: {0}'.format(find_user(self.username)[0])
                else:
                    self.result.status = sky_cfg.API_STATUS_FAIL
                    self.result.output = 'failure to create new user record: {0}'.format(
                        simple_error_format(SkyBaseUserIdNotFoundError(self.username))
                    )
            except (skybase.exceptions.SkyBaseError, sqlite3.Error) as e:
                self.result.output = simple_error_format(e)
                self.result.status = sky_cfg.API_STATUS_FAIL

        else:
            self.result.status = sky_cfg.API_STATUS_SUCCESS
            self.result.output = 'user record to be added: {0}; --apply required'.format(self.username)

        return self.result




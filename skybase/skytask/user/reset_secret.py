import logging
import sqlite3

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger
from skybase.actions.auth.db import unique_user_exists, reset_password
from skybase.actions.user import generate_random_key
from skybase.utils import simple_error_format
import skybase.exceptions

def user_reset_secret_add_arguments(parser):
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
        required = True,
        help='unique username'
    )

    parser.add_argument(
        '-s', '--secret',
        dest='secret',
        action='store',
        help='authentication secret for user'
    )

class ResetSecret(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'user.reset_secret'
        self.args = all_args
        self.runner_cfg = runner_cfg
        self.apply = self.args.get('apply')

        # initialize command options as attributes
        self.username = self.args.get('username')
        # if --secret not provide, generate a new one
        self.secret = self.args.get('secret')


    def preflight_check(self):
        preflight_result = []

        # require that username exists before resetting secret
        if not unique_user_exists(self.username):
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(simple_error_format(
                skybase.exceptions.SkyBaseUserIdNotFoundError(
                    'username {0} not found'.format(self.username))))

        if not self.secret:
            self.secret = generate_random_key()

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):
        """
        reset secret for existing user.
        """
        self.result.format = skytask.output_format_json
        if self.apply:
            try:
                reset_password(self.username, self.secret)
                self.result.output = 'user secret for {0}: {1}'.format(self.username, self.secret)
                self.result.status = sky_cfg.API_STATUS_SUCCESS
            except (skybase.exceptions.SkyBaseError, sqlite3.Error) as e:
                self.result.output = '{0}; (username, secret) = ({1}, {2})'.format(simple_error_format(e), self.username, self.secret)
                self.result.status = sky_cfg.API_STATUS_FAIL
        else:
            self.result.output = 'user secret target for {0}: {1}; --apply required'.format(self.username, self.secret)
            self.result.status = sky_cfg.API_STATUS_SUCCESS
        return self.result




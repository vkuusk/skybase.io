import logging
import sqlite3

from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase import skytask
from skybase.utils.logger import Logger
from skybase.actions.auth.db import list_users
from skybase.utils import simple_error_format
import skybase.exceptions


def user_list_add_arguments(parser):
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
        default='%',
        help='unique username'
    )

class List(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'user.list'
        self.args = all_args
        self.runner_cfg = runner_cfg
        self.username = self.args.get('username')


    def preflight_check(self):
        return self.preflight_check_result


    def execute(self):
        """
        list all users and roles from auth db
        """
        self.result.format = skytask.output_format_json
        try:
            self.result.output = list_users(self.username)
            self.result.status = sky_cfg.API_STATUS_SUCCESS
        except (skybase.exceptions.SkyBaseError, sqlite3.Error) as e:
            self.result.output = simple_error_format(e)
            self.result.status = sky_cfg.API_STATUS_FAIL

        return self.result




import os
import sys

import skybase.schemas
from skybase.utils.schema import read_yaml_from_file
from skybase.utils import simple_error_format
from skybase.exceptions import SkyBaseConfigurationError
from yaml.scanner import ScannerError
from yaml.parser import ParserError

# Application CONSTANTS

# Configuration
DEFAULT_CONFIG_DIR = '/etc/skybase'
CONFIG_DIR = DEFAULT_CONFIG_DIR

# TODO: verify directory existence or error
# use CLI runtime --config option for application config directory default if exists
if '--config' in sys.argv:
    cfg_pos = sys.argv.index('--config')
    CONFIG_DIR = sys.argv[cfg_pos + 1]

# RestAPI
API_SERVER = 'http://localhost:8880'
API_ROOT = 'api'
API_VERSION = '0.1'
API_ROUTES = {
    'task': 'task',
}
API_HTTP_HEADER_SIGNATURE = 'Skybase-Request-Signature'
API_HTTP_HEADER_ACCESS_KEY = 'Skybase-Access-Key'
API_STATUS_SUCCESS = 'success'
API_STATUS_FAIL = 'fail'

# Client
DEFAULT_PLANET = 'dev-aws-us-west-1'

# User Authentication DB

skybase.schemas.set_indicators()

# client config should contain url and credentials for the Skybase REST API and client logging settings
# "default" section should contain default settings for the command line options (currently only planet_name)
# location of the config is $HOME/.skybase/ (unless overriden on the commandline --config_dir=... option
#
# client_config_dir contains 2 files: a) client.yaml; b) credentials.yaml

config_schemas = {
'client': [
    [['restapi_server_url'], []],
    [['log_file'], []],
    [['log_level'], []],
    [['defaults'], []],
    [['defaults', 'planet'], []]
],

'restapi': [
    [['queues'], []],
    [['roles'], []],
],

'runner': [
    [['planet_data_dir'], ['/srv/skybase/data/planets']],
    [['artiball_data_dir'], ['/srv/skybase/data/artiballs']],
    [['std_templates_dir'], ['/srv/skybase/data/templates']],
    [['runner_credentials_dir'], ['/etc/skybase/credentials']],
    [['package_depot_s3_bucket'], ['skybase-artiball-cache']],
    [['package_depot_aws_profile'], ['lithiumdev']]
],

'worker': [],

'credentials': [
    [['user_id'], []],
    [['key'], []],
],

}


class SkyConfig(object):
    # reminder for different types of configs: client_dat, restapi_data, worker_data, topology_data

    def __init__(self, schema_name, config_data=None):
        self.schema = config_schemas[schema_name]
        self.data = config_data


    def get_data_value(self, data_key, data_default=None):
        '''
        attempt to retrieve configuration value by key.  return default if not found.
        '''
        if self.data and self.data.get(data_key):
            data_value = self.data.get(data_key)
        else:
            data_value = data_default
        return data_value


    @classmethod
    def init_from_file(cls, schema_name, config_dir=CONFIG_DIR):
        # prepare configuration filename
        config_file_name = '/'.join([config_dir, schema_name + '.yaml'])
        config_file = os.path.expanduser(config_file_name)

        # read in target configuration filea and attempt to init class
        try:
            runner_config_data = read_yaml_from_file(config_file)
        except (IOError, ScannerError, ParserError) as e:
            # wrap all expected errors as SkyBaseError type
            raise SkyBaseConfigurationError(simple_error_format(e))

        cfg = cls(schema_name, runner_config_data)

        return cfg


import os
import errno

from skybase import config as sky_cfg
import skybase.exceptions


class Install(object):
    def __init__(self, service_name=None, service_dir=None):
        self.service_name = service_name
        self.service_dir = service_dir

    def __repr__(self):
        return str(''.join([self.__class__.__name__, '(', str(self.__dict__), ')']))


class ChefInstall(Install):
    def __init__(self, service_name=None, service_dir=None, **kwargs):
        Install.__init__(self, service_name, service_dir)
        self.cookbooks_dir = kwargs.get('cookbooks_dir')
        self.cookbooks_order_file = kwargs.get('cookbooks_order_file')
        self.databags_dir = kwargs.get('databags_dir')
        self.enc_databags_dir = kwargs.get('enc_databags_dir')
        self.encrypted_data_bag_secret = kwargs.get('encrypted_data_bag_secret')
        self.runner_cfg = sky_cfg.SkyConfig.init_from_file(
            'runner', config_dir=sky_cfg.CONFIG_DIR)

    @property
    def cookbook_path(self):
        return self.get_install_component_path(self.cookbooks_dir)

    @property
    def databags_path(self):
        return self.get_install_component_path(self.databags_dir)

    @property
    def enc_databags_path(self):
        return self.get_install_component_path(self.enc_databags_dir)

    # list all cookbooks
    @property
    def cookbooks(self):
        cb_list = []
        path = self.get_install_component_path(self.cookbooks_dir)
        if os.path.isdir(path):
            cb_list = os.walk(path).next()[1]
        return cb_list

    @property
    def ordered_cookbooks(self):
        cookbook_file = os.path.join(
            self.service_dir,
            self.service_name,
            self.cookbooks_order_file,
        )
        cookbook_list = []

        if os.path.exists(cookbook_file):
            with open(cookbook_file, 'r') as f:
                cookbook_list = [line.strip() for line in f]

        return cookbook_list

    @property
    def databags(self):
        return self.make_databag_list(self.databags_dir)

    @property
    def encrypted_databags(self):
        return self.make_databag_list(self.enc_databags_dir)

    def get_install_component_path(self, subdir):
        return '/'.join([self.service_dir, self.service_name, subdir, ])

    def make_databag_list(self, databags_dir):
        db_list = []
        path = self.get_install_component_path(databags_dir)
        if os.path.isdir(path):
            db_list = [databag for databag in os.listdir(path)
                       if os.path.isdir(os.path.join(path, databag))]
        return db_list

    def get_encrypted_databag_secret_key(self):
        chef_secret_file = os.path.join(
            self.runner_cfg.data['runner_credentials_dir'],
            self.encrypted_data_bag_secret,
        )

        try:
            with open(chef_secret_file, 'r') as f:
                secret = f.readlines()[0]
            return secret

        except IOError as e:
            if e.errno == errno.ENOENT:
                raise skybase.exceptions.SkyBaseDeployError(
                    str('Missing required file: {0}'.format(e.filename)))
            else:
                raise

    # TODO: param format needs to be responsive to orchestration engine differences
    def get_template_params(self):
        parameters = ('ChefEncryptedDataBagSecret', self.get_encrypted_databag_secret_key())
        return parameters
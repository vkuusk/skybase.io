import os
import glob

class App(object):
    def __init__(self, service_name=None, service_dir=None, **kwargs):
        self.service_name = service_name
        self.service_dir = service_dir
        self.code_dir = kwargs.get('code_dir')

    # list all appcode packages
    @property
    def packages(self):
        # return list of all packages in app folder, ignoring subdirs
        package_path = '{0}/*'.format(self.app_path)
        package_list = [os.path.basename(package) for package in glob.glob(package_path)
                        if os.path.isfile(package)]
        return package_list

    @property
    def app_path(self):
        return '/'.join([self.service_dir, self.service_name, self.code_dir])

    def __repr__(self):
        return str(''.join([self.__class__.__name__, '(', str(self.__dict__), ')']))

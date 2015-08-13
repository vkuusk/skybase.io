import os
import sys
import errno
import shutil
import re
import ast
import yaml

from setuptools.command.install import install
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_install_requirements(reqfile):
    with open(reqfile, 'r') as f:
        return [l.strip() for l in f]

# define application name

app_name = 'skybase'
isClient = False
isLithiumProd = True

if len(sys.argv) > 1 and 'client' in sys.argv:
    app_name = 'skybase-client'
    isClient = True

app_egg = app_name + '.egg-info'
# remove previous sdist packaging artifacts before creating new
if 'sdist' in sys.argv:
    try:
        shutil.rmtree(app_egg)
        print 'previous build artifact deleted: {0}'.format(app_egg)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

_version_re = re.compile(r'__version__\s+=\s+(.*)')

current_dir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(current_dir, 'skybase/__init__.py').format(app_name), 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


def copy_configs(profile, client_install):
    target_dir = "/etc/skybase"
    if client_install:
        shutil.copyfile(os.path.join('packaging/configs', profile, 'client.yaml'),
                        os.path.join(target_dir, 'client.yaml'))
        shutil.copyfile(os.path.join('packaging/configs', profile, 'runner.yaml'),
                        os.path.join(target_dir, 'runner.yaml'))


class ClientCommand(install):
    description = 'skybase client install'

    def run(self):
        if not self.dry_run:
            if isClient:
                install.run(self)

class LocalhostCommand(install):
    description = 'create client config pointing to production skybase server'

    def run(self):
        if not self.dry_run:
            copy_configs('localhost', isClient)


setup(
    cmdclass={'client': ClientCommand, 'localhost': LocalhostCommand},
    name=app_name,
    version=version,
    author="CloudOps",
    author_email="cloudops@lithium.com",
    description="https://github.com/lithiumtech/skybase",

    license="apache-v2",
    keywords="devops, cloudops, skybase, deployment",
    url="http://pypi.lcloud.com:8080/simple",

    # prepare list of local packages minus exclusions
    packages=find_packages(where='.', exclude=['bootstrap', 'citools', 'deployments', 'dist', 'docs', 'incubator',
                                               'tests']),

    install_requires=(get_install_requirements(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                            'requirements/client.txt')) if isClient else
                      get_install_requirements(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                            'requirements/restapi.txt'))),

    scripts = ['scripts/sky'] if isClient else
    [
        'scripts/sky',
        'scripts/sky-restapi',
        'scripts/sky-worker',
        'scripts/bootstrap-skybase-client.sh'
    ],

    data_files = [
        ('/var/log/skybase', [],),
        ('/etc/skybase', [],)
    ] if isClient else
    [
        ('/var/log/skybase', [],),
        ('/etc/skybase', [],)
    ],

    package_data={
        '': ['README.md', 'ReleaseNotes.md'],
    },
)
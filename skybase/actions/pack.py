import os
import shutil
import subprocess
import tarfile
import datetime
import urlparse

from distutils import dir_util

from skybase import schemas
from skybase import utils
from skybase.utils import schema as schema_utils
from skybase.operands import artiball as ab_object
from skybase.tools.berkshelf import BerkshelfManager


def init_from_schemas(base_dir, operand, dry_run=False, force=False):
    skybase_dir = os.path.expanduser(base_dir)
    if force:
        dir_util.mkpath(skybase_dir, dry_run=dry_run)
    elif os.path.exists(skybase_dir):
        dir_util.mkpath(skybase_dir, dry_run=True)
    result = schemas.create_dir_tree_from_schema(skybase_dir, operand, dry_run=dry_run, force=force)
    return result


def validate_with_schema(base_dir, operand, update_content_from_config=True):
    result = {"valid": True, "result_string": ""}
    if not os.path.exists(base_dir):
        result["result_string"] += "Cannot find skybase directory to locate artiball\n"
        result["valid"] = False
        return result
    artiball = ab_object.Artiball(base_dir)
    if update_content_from_config:
        artiball.update_content()
        missing_entries = schemas.get_missing_paths_from_schema(base_dir, operand)
        if len(missing_entries) > 0:
            result["valid"] = False
        for missing_entry in missing_entries:
            if '.' in missing_entry.split('/')[-1]:
                result["result_string"] += "Missing file " + missing_entry + '\n'
            else:
                result["result_string"] += "Missing directory " + missing_entry + '\n'
        yaml_files = artiball.yaml_files
    else:
        yaml_files = [os.path.join(base_dir, 'skybase', 'deployment', 'main_deployment.yaml'),
                      os.path.join(base_dir, 'skybase', 'app_config', 'main_app_config.yaml')]

    for yaml_file in yaml_files:
        yaml_result = schemas.validate_yaml_with_schema(yaml_file, 'artiball')
        if not yaml_result["valid"]:
            result["result_string"] += yaml_result["result_string"]
            result["valid"] = False
    return result


def clean(base_dir, dry_run=False, force=True):
    valid = True
    result_string = ""
    if not os.path.exists(base_dir):
        result_string += "Cannot find skybase directory to locate artiball.\n"
        valid = False
        return {"valid": valid, "result_string": result_string}
    files_to_delete = [os.path.join(base_dir, 'manifest.yaml'),
                       os.path.join(base_dir, 'installation', 'chef', 'cookbook-order.yaml')]
    for file in files_to_delete:
        if os.path.exists(file):
            result_string += "Deleting file " + file + "\n"
            if not dry_run:
                if force:
                    utils.schema.delete(file)
                elif os.path.exists(file):
                    result_string += "File " + file + " exists, use --force to override.\n"

    dirs_to_clean = [os.path.join(base_dir, "package"),
                     os.path.join(base_dir, "app")]

    for directory in dirs_to_clean:
        if os.path.exists(directory):
            for content in os.listdir(directory):
                result_string += "Deleting content in " + os.path.join(directory, content) + "\n"
                if not dry_run:
                    if force:
                       utils.schema.delete(os.path.join(directory, content))
                    elif os.path.exists(file):
                        result_string += "File " + os.path.join(directory, content) +\
                                         " exists, use --force to override.\n"

    return {"valid": valid, "result_string": result_string}


def pack(base_dir, app_source, chef_repo, chef_repo_branch, cookbooks, use_berkshelf, databags, encrypted_databags,
         manifest, dry_run=False, verbose=False):
    valid = True
    result_string = ""
    #copy app source
    if app_source is not None:
        if app_source[0] != '/':
            app_source = os.path.join(base_dir, app_source)
        if os.path.isdir(app_source):
            result_string += "Copying application source from directory " + app_source + "\n"
            if not dry_run:
                schema_utils.copy(app_source, os.path.join(base_dir, "app"))
        else:
            result_string += "Copying application source from file " + app_source + "\n"
            if not dry_run:
                shutil.copy(app_source, os.path.join(base_dir, "app"))

    tmp_dir = os.path.join(base_dir, "tmp")
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)
    if chef_repo:
        if chef_repo.startswith('file://'):
            repo = urlparse.urlparse(chef_repo)
            if repo.netloc.startswith('.'):
                repo_name = os.path.join(base_dir, repo.netloc + repo.path)
            else:
                repo_name = os.path.join(repo.netloc, repo.path)
        else:
            result_string += "Cloning cookbooks from repository " + chef_repo + "\n"
            if chef_repo_branch:
                proc = subprocess.Popen(['git', 'clone', '-b', chef_repo_branch, '--depth', '1', chef_repo],
                                        stdout=subprocess.PIPE, cwd=tmp_dir)
            else:
                proc = subprocess.Popen(['git', 'clone', '--depth', '1', chef_repo], stdout=subprocess.PIPE, cwd=tmp_dir)

            proc.communicate()
            rc = proc.returncode
            if rc is not 0:
                result_string += "Failed to git clone." + "\n"
                valid = False
                return {"valid": valid, "result_string": result_string}

            repo_name = chef_repo.strip().split('/')[-1].split('.')[0]

        #copy cookbooks
        if cookbooks:
            if chef_repo:
                if chef_repo.startswith('file://'):
                    cookbooks_root_directory = os.path.join(repo_name, 'cookbooks')
                else:
                    cookbooks_root_directory = os.path.join(tmp_dir, repo_name, 'cookbooks')

                cookbooks_order_file = os.path.join(base_dir, 'installation', 'chef', 'cookbook-order.yaml')
                if use_berkshelf:
                    #generate ordered cookbook dependency list
                    berkshelf_manager = BerkshelfManager(cookbooks, berkshelf_config_path=None, berkshelf_install_path=None)
                    result_string += "Creating cookbooks order list file : " + cookbooks_order_file + "\n"
                    berkshelf_manager.generateOrderedList(cookbooks_root_directory, cookbooks_order_file, dry_run=dry_run)

                #copy dependency cookbooks
                for cookbook in cookbooks:
                    result_string += "Processing dependencies for cookbook: " + cookbook.rstrip('\n') + "\n"
                    if use_berkshelf:
                        for directory in os.listdir(os.path.join(base_dir, 'installation', 'chef', 'cookbooks')):
                            if not dry_run:
                                utils.schema.delete(os.path.join(base_dir, 'installation', 'chef', 'cookbooks', directory))
                        cookbooks_directory = berkshelf_manager.generateCookbooksPackage(cookbooks_root_directory, cookbook)
                        for directory in os.listdir(cookbooks_directory):
                            result_string += "Adding cookbook " + directory + "\n"
                            if chef_repo:
                                if not dry_run:
                                    utils.schema.copy(os.path.join(cookbooks_directory, directory),
                                                      os.path.join(base_dir, 'installation', 'chef', 'cookbooks', directory))
                    elif os.path.exists(cookbooks_order_file):
                        tmp_cookbooks_directory = os.path.join(cookbooks_root_directory, 'cookbooks_tmp')
                        for directory in os.listdir(os.path.join(base_dir, 'installation', 'chef', 'cookbooks')):
                            if not dry_run:
                                utils.schema.delete(os.path.join(base_dir, 'installation', 'chef', 'cookbooks', directory))
                        if not os.path.exists(tmp_cookbooks_directory):
                            os.makedirs(tmp_cookbooks_directory)
                        with open(cookbooks_order_file) as f:
                            dependencies = f.readlines()
                            for dep in dependencies:
                                dep_cookbook_directory = os.path.join(cookbooks_root_directory, dep.rstrip('\n'))
                                if os.path.exists(dep_cookbook_directory):
                                    tmp_cookbook_directory = os.path.join(tmp_cookbooks_directory, dep.rstrip('\n'))
                                    if not os.path.exists(tmp_cookbook_directory):
                                        os.makedirs(tmp_cookbook_directory)
                                    utils.schema.copy(dep_cookbook_directory, tmp_cookbook_directory)
                                else:
                                    result_string += "Cannot find required cookbook " + dep_cookbook_directory + ".\n"
                                    utils.schema.delete(tmp_cookbooks_directory)
                                    valid = False
                                    return {"valid": valid, "result_string": result_string}

                        f.close()
                        for directory in os.listdir(tmp_cookbooks_directory):
                            result_string += "Adding cookbook " + directory + "\n"
                            if chef_repo:
                                if not dry_run:
                                    utils.schema.copy(os.path.join(tmp_cookbooks_directory, directory),
                                                      os.path.join(base_dir, 'installation', 'chef', 'cookbooks', directory))
                        shutil.rmtree(tmp_cookbooks_directory)

                    else:
                        result_string += "dependencies_from_berkshelf is set to False, if you are dependent on chef server, " \
                                         "please create upload order list in : " + \
                                         os.path.join(base_dir, 'installation', 'chef', 'cookbook-order.yaml') + "\n"
                        if os.path.abspath(cookbooks_root_directory) !=\
                                os.path.abspath(os.path.join(base_dir, 'installation', 'chef', 'cookbooks')):
                            for directory in os.listdir(cookbooks_root_directory):
                                result_string += "Adding cookbook " + directory + "\n"
                                if chef_repo:
                                    if not dry_run:
                                        utils.schema.copy(os.path.join(cookbooks_root_directory, directory),
                                                          os.path.join(base_dir, 'installation', 'chef', 'cookbooks', directory))

        if chef_repo:
            databags_root_directory = os.path.join(tmp_dir, repo_name)
            #copy data bags
            if databags:
                for databag in databags:
                    result_string += "Adding data bag : " + databag.rstrip('\n') + "\n"
                    if chef_repo:
                        databag_source_directory = os.path.join(databags_root_directory, "data_bags", databag.rstrip('\n'))
                        if os.path.exists(databag_source_directory):
                            databag_directory = os.path.join(base_dir, 'installation', 'chef', 'databags', databag.rstrip('\n'))
                            if not dry_run:
                                if not os.path.exists(databag_directory):
                                    os.makedirs(databag_directory)
                                utils.schema.copy(databag_source_directory, databag_directory)

            #copy encrypted data bags
            if encrypted_databags:
                for databag in encrypted_databags:
                    result_string += "Adding encrypted data bag : " + databag.rstrip('\n') + "\n"
                    if chef_repo:
                        databag_source_directory = os.path.join(databags_root_directory, "data_bags", databag.rstrip('\n'))
                        if os.path.exists(databag_source_directory):
                            databag_directory = os.path.join(base_dir, 'installation', 'chef',
                                                             'encrypted_databags', databag.rstrip('\n'))
                            if not dry_run:
                                if not os.path.exists(databag_directory):
                                    os.makedirs(databag_directory)
                                utils.schema.copy(databag_source_directory, databag_directory)

        utils.schema.delete(tmp_dir)

    #generate package
    package_dir = os.path.join(base_dir, 'package')
    result_string += '\nPackage location : ' + package_dir + '\n'
    if not dry_run:
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)

    d = datetime.datetime.now()
    timestamp = ''
    for attr in ['year', 'month', 'day', 'hour', 'minute', 'second']:
        timestamp += '%02d' % getattr(d, attr)

    artiball_file_name = str(manifest['metadata']['app_name']) + '_'\
                        + str(manifest['metadata']['app_version']) + '-'\
                        + str(manifest['metadata']['build_id']) + '-'\
                        + str(timestamp) + '.tar.gz'

    # make a short name without '.tar.gz' for use in the commands
    suffix = '.tar.gz'
    ab_short_name = artiball_file_name[:-len(suffix)]

    if not dry_run:
        tar = tarfile.open(os.path.join(package_dir, artiball_file_name), "w:gz")

        def excludes_fn(name):
            return (('package' in name) and os.path.isdir(name)) \
                   or ('skybase.yaml' in name)
        tar.add(base_dir, arcname='', exclude=excludes_fn)

        tar.close()
        if verbose:
            sep_len = 60
            result_string += str('\n' + '*' * sep_len + '\n')
            result_string += '\nARTIBALL : ' + ab_short_name + '\n'
            result_string += str('\n' + '-' * sep_len + '\n')
            result_string += '\nUPLOAD and SUBMIT the ARTIBALL using TWO COMMANDS : \n'
            result_string += str('\n' + '-' * sep_len + '\n')
            result_string += '\nsky pack upload -a ' + ab_short_name + '\n'
            result_string += '\nsky pack submit -a ' + ab_short_name + '\n'
            result_string += str('\n' + '*' * sep_len + '\n')
        else:
            result_string = ab_short_name
    else:
        result_string += '\nIf not "dry-run" then would create ARTIBALL : ' + ab_short_name + '\n'

    return {"valid": valid, "result_string": result_string}
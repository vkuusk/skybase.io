import sys
import logging
import os
import subprocess
import tarfile
import itertools

from collections import defaultdict

from skybase.utils import schema as schema_utils


class BerkshelfManager:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    cookbooks = []
    berkshelf_config_path = ''

    def __init__(self, cookbooks, berkshelf_config_path=None, berkshelf_install_path=None):
        self.cookbooks = cookbooks

        if berkshelf_config_path is None:
            self.berkshelf_config_path = os.path.join(os.path.expanduser("~"), ".berkshelf", "config.json")
        else:
            self.berkshelf_config_path = berkshelf_config_path

        if berkshelf_install_path is None:
            berkshelf_install_path = "/usr/bin"
        sys.path.append(berkshelf_install_path)

    @staticmethod
    def getNumWhite(self, line):
        return len(line) - len(line.lstrip())

    @staticmethod
    def getList(self, cookbook, cookbookList, cookbookMatrix, printed, outfile):
        for c in cookbookList:
            # if cookbook has dependencies, recurse on each dependency
            if (cookbookMatrix[cookbook, c] == 1):
                self.getList(self, c, cookbookList, cookbookMatrix, printed, outfile)
        if cookbook not in printed:
            outfile.write("%s\n" % cookbook)
            printed.append(cookbook)


    def generateCookbooksPackage(self, cookbook_repo_dir, cookbook):
        # run berks package
        self.logger.debug("running berks package from cookbook " + cookbook)
        proc = subprocess.Popen(['berks', 'package', '-c',
                                 self.berkshelf_config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=os.path.join(cookbook_repo_dir, cookbook))

        tmp = proc.stdout.read()
        proc.communicate()
        rc = proc.returncode

        if rc is not 0:
            self.logger.error("failed to run berks package")
            sys.exit(rc)

        package_path = tmp.splitlines()[-1].split(' ')[3]
        cookbooks_tar = tarfile.open(package_path)
        cookbooks_tar.extractall(path=package_path.split('.tar.gz')[0])
        cookbooks_tar.close
        schema_utils.delete(os.path.join(package_path.split('.tar.gz')[0], "cookbooks", 'Berksfile.lock'))
        schema_utils.delete(package_path)
        return package_path.split('.tar.gz')[0] + os.sep + "cookbooks"


    def generateOrderedList(self, cookbook_repo_dir, outfile, dry_run=False):
        final_cookbook_list = []
        final_cookbook_matrix = defaultdict(int)
        for cookbook in self.cookbooks:
            cookbook_directory = os.path.join(cookbook_repo_dir, cookbook)
            if os.path.exists(cookbook_directory):
                self.logger.info("generating dependency ordered list from cookbook: " + cookbook)
                berks_lock_path = os.path.join(cookbook_repo_dir, cookbook, 'Berksfile.lock')
                try:
                    os.remove(berks_lock_path)
                except OSError:
                    pass

                # run berks install
                self.logger.debug("running berks install from cookbook " + cookbook)
                proc = subprocess.Popen(['berks', 'install', '-c', self.berkshelf_config_path],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        cwd=os.path.join(cookbook_repo_dir, cookbook))

                tmp = proc.stdout.read()
                err = proc.stderr.read()
                proc.communicate()
                rc = proc.returncode

                if rc is not 0:
                    self.logger.error(err)
                    self.logger.error("failed to run berks install")
                    quit(rc)

                cookbook_matrix = defaultdict(int)
                cookbook_list = []

                # read Berksfile.lock to get complete dependency list
                with open(berks_lock_path, "r") as lock_file:

                    dep_graph = lock_file.read().split("GRAPH")[1].split('\n')
                    dep_graph = filter(None, dep_graph)

                    prev_num_white = self.getNumWhite(self, dep_graph[0])
                    prev_cookbook = dep_graph[0].lstrip().split(" ")[0]
                    parent_cookbook = ""
                    isDep = False

                    for line in dep_graph:
                        if self.getNumWhite(self, line) > prev_num_white:
                            parent_cookbook = prev_cookbook
                            isDep = True
                        elif self.getNumWhite(self, line) < prev_num_white:
                            isDep = False

                        curr_cookbook = line.lstrip().split(" ")[0]
                        if isDep:
                            cookbook_matrix[parent_cookbook, curr_cookbook] += 1

                        prev_cookbook = curr_cookbook
                        cookbook_list.append(curr_cookbook)
                        prev_num_white = self.getNumWhite(self, line)
                lock_file.close()

                for k, v in itertools.chain(final_cookbook_matrix.iteritems(), cookbook_matrix.iteritems()):
                    final_cookbook_matrix[k] = v

                cookbook_list = list(set(cookbook_list))
                final_cookbook_list = sorted(final_cookbook_list + cookbook_list)
            else:
                sys.exit("failed to find following cookbook in repository: " + cookbook_directory)


        # output to file
        if not dry_run:
            with open(outfile, 'w') as outfile:
                printed = []
                for cookbook in final_cookbook_list:
                    self.getList(self, cookbook, final_cookbook_list, final_cookbook_matrix, printed, outfile)
            outfile.close()


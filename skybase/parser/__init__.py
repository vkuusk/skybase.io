import argparse
import sys
import json
import importlib
import pkgutil

from skybase import config as sky_cfg
from skybase import __version__ as SKYBASE_VERSION

common_parser = argparse.ArgumentParser(add_help=False)
common_parser.add_argument(
    '--config',
    dest='config_dir',
    action='store',
    default=sky_cfg.DEFAULT_CONFIG_DIR,
    help='location of skybase configuration files'
)

common_parser.add_argument(
    '--no-wait',
    dest='nowait',
    action='store_true',
    default=False,
    help='do not wait for command results. Effective for REST API calls and some tasks in local mode'
)

common_parser.add_argument(
    '--apply',
    dest='apply',
    action='store_true',
    default=False,
    help='apply command'
)

common_parser.add_argument(
    '--creds',
    dest='creds_dir',
    action='store',
    default='~/.skybase',
    help='location of skybase user id and authentication key'
)


def parse_skycmd_argv():

    import skybase.skytask as tasks

    # Create and instance of parser here, then add all subparsers in local cycle and
    # and for each subparser add_arguments using auto-generated names of methods in Task Modules / group and commands
    #  the methods accept parser as an argument
    # pack_init_add_arguments(parser)
    # so object are created here but modified in other files

    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    subparsers = parser.add_subparsers(help='group', dest='command_group')

    # location to the directory with all tasks
    tasks_module = 'skybase.skytask'
    # suffix for the add_arguments function name inside each module for a command
    add_args_function_suffix = '_add_arguments'

    for group_importer, group_name, group_ispkg in pkgutil.iter_modules(tasks.__path__):

        group_module_name = '.'.join([tasks_module, group_name])
        group_module = importlib.import_module(group_module_name)

        group_add_args_func = group_module.__dict__.get(group_name + add_args_function_suffix)

        option_name = module_to_option_name(group_name)
        group_parser = subparsers.add_parser(option_name)
        if group_add_args_func is not None:
            group_add_args_func(group_parser)

        group_subparsers = group_parser.add_subparsers(dest='command_name')

        for command_importer, command_name, command_ispkg in pkgutil.iter_modules(group_module.__path__):

            command_module_name = '.'.join([tasks_module, group_name, command_name])
            command_module = importlib.import_module(command_module_name)

            command_add_args_func = command_module.__dict__.get(group_name + '_' + command_name + '_add_arguments')

            option_name = module_to_option_name(command_name)
            command_parser = group_subparsers.add_parser(option_name, parents=[common_parser])

            if command_add_args_func is not None:
                command_add_args_func(command_parser)

    # print help if no "-h" is specified
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    #
    if (len(sys.argv) == 2) and ((sys.argv[1] == '-v') or (sys.argv[1] == '--version')):
            print 'Skybase Client Version: ', SKYBASE_VERSION
            sys.exit(0)

    #  brute force (for now) to print help for the group of the commands
    if (len(sys.argv) == 2) and (not sys.argv[1] == '-h') and (not sys.argv[1] == '--help'):
        try:
            get_group_parser_by_name(parser, sys.argv[1]).print_help()
            sys.exit(0)
        except:
            # let ArgumentParser handle the unknown
            pass


    # TODO: insert this function into -h or --help of the ArgumentParser itself (later)
    if (len(sys.argv) == 2) and ((sys.argv[1] == '-h') or (sys.argv[1] == '--help')):
        if len(sys.argv) < 3:
            # retrieve subparsers from parser
            subparsers_actions = [
                action for action in parser._actions
                if isinstance(action, argparse._SubParsersAction)]
            # there will probably only be one subparser_action,
            # but better save than sorry
            for subparsers_action in subparsers_actions:
                # get all subparsers and print help
                for choice, subparser in subparsers_action.choices.items():
                    print("\n\nCommand Group ---------- '{}'".format(choice))
                    print(subparser.format_help())
            sys.exit(0)

    all_args = parser.parse_args()

    # Do some checks on arguments or some args processing
    # Nothing for now

    return all_args

def get_group_parser_by_name(parser, name):

    # TODO: review later. for now returning first found _SubParsersAction
    # usually it's only one anyway
    for action in parser._subparsers.__dict__['_actions']:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[name]

def module_to_option_name(module_name):
    '''
    Converts module name with underscores to the corresponding name with dashes

    :param module_name:
    :return: option_name
    '''

    option_name = '-'.join(module_name.split('_'))

    return option_name


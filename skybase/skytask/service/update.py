import logging
import os

import yaml
import boto.exception

import skybase.actions.state
import skybase.actions.skycloud
import skybase.actions.skychef
import skybase.actions.salt
from skybase import config as sky_cfg
from skybase.skytask import SkyTask
from skybase.utils.logger import Logger
from skybase import skytask
from skybase.service import SkyService, SkyRuntime, SkySystem
from skybase.utils import simple_error_format, all_true
from skybase.planet import Planet
from skybase.actions.skyenv import artiball_transfer
from skybase.api.salt import SkySaltAPI
from skybase.exceptions import SkyBaseError, SkyBaseValidationError, StateDBRecordNotFoundError

# TODO: plans will need to be in a namespace for each type: skybase, service, &c
# TODO: correct location for plan data
skybase_update_plans = {
    'rerun': '/srv/skybase/chef-rerun.sh',
}

def service_update_add_arguments(parser):

    parser.add_argument(
        '-i', '--id',
        dest='skybase_id',
        action='store',
        required=True,
        help='target skybase service registry id')

    parser.add_argument(
        '-a', '--artiball',
        dest='source_artiball',
        action='store',
        required=True,
        help='source artiball used to update existing service'
    )

    parser.add_argument(
        '-k', '--stack-name',
        dest='stack_list',
        default=[],
        action='append',
        help='provide one or many stack names each with a separate option'
    )

    parser.add_argument(
        '-p', '--planet',
        dest='planet_name',
        action='store',
        required=True,
        help='planet name (required).'
    )

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )

    parser.add_argument(
        '--update-plan',
        dest='update_plan',
        action='store',
        choices=set(skybase_update_plans.keys()),
        default=None,
        help='update using plan'
    )

class Update(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'service.update'
        self.args = all_args
        self.runner_cfg = runner_cfg

        # required attributes derived from command arguments
        self.mode = self.args.get('exec_mode', False)
        self.runtime = SkyRuntime(apply=self.args.get('apply', False))
        self.system = SkySystem()
        self.chef_type = None

        self.id = self.args.get('skybase_id')
        self.target_service = None
        self.target_planet = None

        self.source_artiball = self.args.get('source_artiball')
        self.source_service = None

        self.planet_name = self.args.get('planet_name')
        self.planet = None

        self.update_plan = self.args.get('update_plan')

    def preflight_check(self):
        preflight_result = []

        # TODO: move reusable preflight functions/tests to skybase.skytask.service
        # instantiate planet from --planet option
        try:
            self.planet = Planet(self.planet_name)
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(SkyBaseValidationError('source planet init: {0}'.format(simple_error_format(e))))

        try:
            # attempt transfer artiball to worker
            if not os.path.exists(os.path.join(self.runner_cfg.data['artiball_data_dir'], self.args.get('source_artiball'))):
                artiball_transfer(
                    artiball_key=self.args.get('source_artiball'),
                    bucket_name=self.runner_cfg.data['buckets']['cache']['name'],
                    profile=self.runner_cfg.data['buckets']['cache']['profile'],
                    release_dir=self.runner_cfg.data['artiball_data_dir'])
        except boto.exception.S3ResponseError as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(SkyBaseValidationError('artiball transfer: {0}: {1}'.format(type(e).__name__, str(e.message))))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(SkyBaseValidationError('artiball transfer: {0}'.format(simple_error_format(e))))
        else:
            # initialize SkyService from source artiball
            try:
                self.source_service = SkyService().init_from_artiball(
                    artiball_name=self.source_artiball,
                    artiball_data_dir=self.runner_cfg.data['artiball_data_dir']
                )
                self.chef_type = self.source_service.deploy.definition.get('chef_type', 'server')
            except Exception as e:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(SkyBaseValidationError('sky service init: {0}'.format(simple_error_format(e))))
            else:

                # test CLI stack option values against SkyService stacks
                try:
                    bad_stacks = []
                    for stack in self.args['stack_list']:
                        if stack not in self.source_service.deploy.stack_ids:
                            bad_stacks.append(stack)

                    if bad_stacks:
                        self.preflight_check_result.status = 'FAIL'
                        preflight_result.append(SkyBaseValidationError('source service {0}: unknown stacks {1}'.format(self.source_service.name, bad_stacks)))
                    else:
                        # given all good stacks, prepare stack launch list target
                        self.source_service.deploy.stack_launch_list = self.args['stack_list'] if self.args['stack_list'] else self.source_service.deploy.stack_ids

                except Exception as e:
                    self.preflight_check_result.status = 'FAIL'
                    preflight_result.append(SkyBaseValidationError('source stack verification: {0}'.format(simple_error_format(e))))


        # attempt to read state db record
        try:
            serialized_record = skybase.actions.state.read(
                mode=self.mode,
                record_id=self.id,
                credentials=sky_cfg.SkyConfig.init_from_file('credentials').data,
                format='yaml'
            )

            # DECISION: need general method for processing API in-flight errors
            if serialized_record.startswith('StateDBRecordNotFoundError'):
                raise StateDBRecordNotFoundError(self.id)

        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(SkyBaseValidationError(simple_error_format(e)))
        else:
            try:
                self.target_service = yaml.load(serialized_record)
                self.runtime.tag = self.target_service.tag
            except Exception as e:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(SkyBaseValidationError('service registry init: {0}'.format(simple_error_format(e))))
            else:
                try:
                    bad_stacks = []
                    for stack in self.source_service.deploy.stack_launch_list:
                        if stack not in self.target_service.stacks.deployed_stacks:
                            bad_stacks.append(stack)

                    if bad_stacks:
                        self.preflight_check_result.status = 'FAIL'
                        preflight_result.append(SkyBaseValidationError('target service {0}: stacks not deployed {1}'.format(self.target_service.service, bad_stacks)))

                except Exception as e:
                    self.preflight_check_result.status = 'FAIL'
                    preflight_result.append(SkyBaseValidationError('target stack verification: {0}'.format(simple_error_format(e))))

            # instantiate planet based on service registry value
            try:
                self.target_planet = Planet(self.target_service.planet)
            except Exception as e:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(SkyBaseValidationError('target planet init: {0}'.format(simple_error_format(e))))
            else:
                if self.planet.planet_name != self.target_planet.planet_name:
                    self.preflight_check_result.status = 'FAIL'
                    preflight_result.append('source planet {0} not equal target planet {1}'.format(self.planet.planet_name, self.target_planet.planet_name))

            # test if existing service can be updated
            if self.source_service and self.target_service:
                # TODO: test that target and source service names match!
                is_version_ok = (self.source_service.manifest.get('app_version') >= self.target_service.metadata.version)
                if not is_version_ok:
                    self.preflight_check_result.status = 'FAIL'
                    preflight_result.append(SkyBaseValidationError('source < target service version: {0} < {1}'.format(self.source_service.manifest.get('app_version'), self.target_service.metadata.version)))
            else:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(SkyBaseValidationError('cannot update service: missing (target / source): ({0} / {1})'.format(self.target_service == None, self.source_service == None)))

        try:
            # acquire salt API authtoken
            self.authtoken = skybase.actions.salt.get_saltapi_authtoken(runner_cfg=self.runner_cfg, planet_name=self.target_service.planet)
            if self.authtoken is None:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(SkyBaseValidationError('failed to login to salt API'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(SkyBaseValidationError('failed to acquire salt API authtoken: {0}'.format(simple_error_format(e))))

        else:

            for stack in self.source_service.deploy.stack_launch_list:
                stack_roles = self.target_service.blueprint.get_stack_roles(stack)

                for role in stack_roles:
                    stack_role_grain = self.target_service.stacks.stacks[stack].get_stack_role_salt_grain_skybase_id(role)

                    try:
                        saltapi_result = skybase.actions.salt.test_ping_by_grain(
                            grain=stack_role_grain,
                            authtoken=self.authtoken,
                            planet_name=self.target_service.planet,
                        )

                    except Exception as e:
                        self.preflight_check_result.status = 'FAIL'
                        preflight_result.append(SkyBaseValidationError('saltapi test.ping: {0}'.format(simple_error_format(e))))

                    else:
                        # verify that some minions were targeted
                        if saltapi_result[0] != SkySaltAPI.NO_MINIONS:
                            # verify all minions reply returned True to ping
                            if not all(saltapi_result[0].values()):
                                self.preflight_check_result.status = 'FAIL'
                                preflight_result.append(SkyBaseValidationError(
                                    'unreachable salt minions for stack-role {0}-{1} using grain {2}: {3}'.format(stack, role, stack_role_grain, saltapi_result)))
                        else:
                            self.preflight_check_result.status = 'FAIL'
                            preflight_result.append(SkyBaseValidationError('{0} using grain: {1}'.format(SkySaltAPI.NO_MINIONS, stack_role_grain)))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):
        self.result.output = dict()
        self.result.format = skytask.output_format_json

        self.result.output['chef_update'] = skybase.actions.skychef.chef_update(
            planet=self.planet,
            service=self.source_service,
            runtime=self.runtime,
            config=self.runner_cfg,
        )

        self.result.output['package_transfer'] = skybase.actions.skycloud.package_transfer(
            planet=self.planet,
            service=self.source_service,
            runtime=self.runtime,
            system=self.system,
        )

        self.result.output['salt_grains_transfer'] = skybase.actions.skycloud.salt_grains_transfer(
            planet=self.planet,
            service=self.source_service,
            runtime=self.runtime,
            system=self.system,
        )

        self.result.output['salt_update_service'] = skybase.actions.salt.update_service(
            service=self.target_service,
            stacks=self.source_service.deploy.stack_launch_list,
            runtime=self.runtime,
            update_plan=self.update_plan,
            authtoken=self.authtoken,
        )

        # modify service registry record on successful update
        if self.runtime.apply:
            self.target_service.metadata.version = self.source_service.manifest.get('app_version')
            self.target_service.metadata.build = self.source_service.manifest.get('build_id')
            self.target_service.metadata.artiball = self.source_artiball

            # attempt to update state db record
            try:
                self.result.output['update_service_registry'] = \
                    skybase.actions.state.update(
                        mode=self.mode,
                        record_id=self.id,
                        service_record=self.target_service.serialize_as_yaml(),
                        credentials=sky_cfg.SkyConfig.init_from_file('credentials').data,
                    )
            except SkyBaseError as e:
                self.result.output['update_service_registry'] = simple_error_format(e)

        self.result.format = skytask.output_format_json
        return self.result

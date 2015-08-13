import logging
import os

import skybase
import skybase.exceptions
import skybase.actions.skychef
import skybase.actions.skycloud
import skybase.actions.skyenv
from skybase.skytask import SkyTask
from skybase.utils.logger import Logger
from skybase import config as sky_cfg
from skybase import skytask
from skybase.planet import Planet
from skybase.service import SkyService, SkyRuntime, SkySystem
from skybase.utils import simple_error_format


def service_deploy_add_arguments(parser):

    parser.add_argument(
        '-p', '--planet',
        dest='destination_planet',
        action='store',
        default=sky_cfg.DEFAULT_PLANET,
        help='planet name (required).'
    )

    parser.add_argument(
        '-a', '--artiball',
        dest='source_artiball',
        action='store',
        required=True,
        help='Packaged Release Bundle Name (required)'
    )

    parser.add_argument(
        '-k', '--stack-name',
        dest='stack_list',
        default=[],
        action='append',
        help='provide one or many stack names each with a separate option'
    )

    parser.add_argument(
        '-r', '--runtime',
        dest='runtime',
        default=[],
        action='append',
        help='provide one or many runtime option in form Key=Value'
    )

    parser.add_argument(
        '-t', '--tag',
        dest='tag',
        action='store',
        required=True,
        help='deployment tag included in stack id (required)')

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )

class Deploy(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'service.deploy'
        self.args = all_args
        self.runner_cfg = runner_cfg

        # required attributes derived from command arguments
        self.planet = None
        self.service = None

        # create runtime object with command options
        self.runtime = SkyRuntime(
            tag=all_args.get('tag'),
            apply=all_args.get('apply', False))

        self.system = SkySystem()

    def preflight_check(self):
        # initialize results container
        preflight_result = []

        # instantiate planet
        try:
            self.planet = Planet(self.args.get('destination_planet'))
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('planet init: {0}'.format(simple_error_format(e))))

        # TODO: should artiball transfer  *always* occur? OR attempt comparison timestamp / fingerprint to limit?
        # attempt transfer artiball to worker
        try:
            if not os.path.exists(os.path.join(self.runner_cfg.data['artiball_data_dir'], self.args.get('source_artiball'))):
                skybase.actions.skyenv.artiball_transfer(
                    artiball_key=self.args.get('source_artiball'),
                    bucket_name=self.runner_cfg.data['buckets']['cache']['name'],
                    profile=self.runner_cfg.data['buckets']['cache']['profile'],
                    release_dir=self.runner_cfg.data['artiball_data_dir']
                )
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('artiball transfer: {0}'.format(simple_error_format(e))))

        # initialize SkyService using --artiball value
        try:
            self.service = SkyService().init_from_artiball(
                artiball_name=self.args.get('source_artiball'),
                artiball_data_dir=self.runner_cfg.data['artiball_data_dir']
            )
            # check planet trusted chef cookbook source against artiball's metadata when running chef-server mode
            if self.service.deploy.definition.get('chef_type', 'server') == 'server':
                cookbook_source = self.service.manifest['chef_cookbook_source']
                trusted_cookbook_source = self.planet._yaml_data['services']['chefserver']['trusted_chef_cookbook_source']
                if cookbook_source not in trusted_cookbook_source:
                    self.preflight_check_result.status = 'FAIL'
                    preflight_result.append('untrusted chef cookbook source in artiball: ' + cookbook_source)
        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('sky service init: {0}'.format(simple_error_format(e))))


        # test CLI stack option values against SkyService stacks
        try:
            bad_stacks = []
            for stack in self.args['stack_list']:
                if stack not in self.service.deploy.stack_ids:
                    bad_stacks.append(stack)

            if bad_stacks:
                self.preflight_check_result.status = 'FAIL'
                preflight_result.append(skybase.exceptions.SkyBaseValidationError('service {0}: unknown stacks {1}'.format(self.service.name, bad_stacks)))
            else:
                # given all good stacks, prepare stack launch list target
                self.service.deploy.stack_launch_list = self.args['stack_list'] if self.args['stack_list'] else self.service.deploy.stack_ids

        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('stack verification: {0}'.format(simple_error_format(e))))

        # prepare runtime
        try:
            # push client runtime options into runtime object
            runtime_unpacked = dict(attr.split('=') for attr in self.args.get('runtime'))
            self.runtime.set_attrs(**runtime_unpacked)

        except Exception as e:
            self.preflight_check_result.status = 'FAIL'
            preflight_result.append(skybase.exceptions.SkyBaseValidationError('runtime: {0}'.format(simple_error_format(e))))

        self.preflight_check_result.set_output(preflight_result)
        return self.preflight_check_result


    def execute(self):

        self.result.output = dict()
        self.result.format = skytask.output_format_json

        self.result.output['chef_update'] = skybase.actions.skychef.chef_update(
            planet=self.planet,
            service=self.service,
            runtime=self.runtime,
            config=self.runner_cfg,
        )

        self.result.output['package_transfer'] = skybase.actions.skycloud.package_transfer(
            planet=self.planet,
            service=self.service,
            runtime=self.runtime,
            system=self.system,
        )

        self.result.output['salt_grains_transfer'] = skybase.actions.skycloud.salt_grains_transfer(
            planet=self.planet,
            service=self.service,
            runtime=self.runtime,
            system=self.system,
        )

        self.result.output['launch_stacks'] = skybase.actions.skycloud.launch_stacks(
            planet=self.planet,
            service=self.service,
            runtime=self.runtime,
            system=self.system,
        )

        if self.runtime.apply:
            # prepare task to record deployment outcome to service registry
            self.result.next_task_name = 'service.record_state'

            self.result.next_args = {
                'planet_name': self.planet.planet_name,
                'service_name': self.service.deploy.definition.get('service_name'),
                'deploy_tag': self.runtime.tag,
                'registration': self.service.registration,
                'provider_name': self.planet.provider,
                'stacks': self.result.output['launch_stacks']['stacks']
            }

        return self.result
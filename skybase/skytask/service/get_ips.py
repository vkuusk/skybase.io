import logging

from skybase.skytask import SkyTask
from skybase.planet import Planet
from skybase.utils.logger import Logger
from skybase import skytask
from skybase.actions.dbstate import PlanetStateQueryTypes, PlanetStateDbQuery
from skybase.actions.skycloud import call_cloud_api

def service_get_ips_add_arguments(parser):
    parser.add_argument(
        '-i', '--id',
        dest='skybase_id',
        action='store',
        required=True,
        help='skybase service registry id')

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )


class GetIps(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'service.get_ips'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def preflight_check(self):
        return self.preflight_check_result

    def execute(self):
        # initialize service status query using skybase service registry id
        query = PlanetStateDbQuery.init_from_id(
            self.args['skybase_id'],
            query_type = PlanetStateQueryTypes.WILDCARD)

        # execute query and return standard result
        query_result = query.format_result_set(query.execute())

        # tabular output header
        service_output = '\n{0}\t\t{1}\t\t{2}\n\n'.format('ip_address', 'role_name', 'stack_name')

        # gather and format state information for each stack, role, and
        # instance ip address for query result
        for result in query_result:

            # unpack query result
            recid, instance_info = result.items()[0]
            stackname = instance_info['cloud']['stack_name']

            # TODO: performance / DRY enhancement: register planet and only init when not present
            planet_name = recid.split('/')[1]
            planet = Planet(planet_name)

            # get stack status
            stack_status = call_cloud_api(
                    planet=planet,
                    stack_name=stackname,
                    action='get_stack_status',
            )

            # report state information if stack launch complete
            stack_output = ''
            if stack_status == 'CREATE_COMPLETE':
                # call cloud provider for ip addresses
                stack_info = call_cloud_api(
                    planet=planet,
                    stack_name=stackname,
                    action='get_instance_ip',
                )
                
                # parse stack, role, instance info for ip addresses and
                # present in tabular format
                for instance_role_name, instances in stack_info.items():
                    # prepare output line for each ip address
                    for inst in instances:
                        # prepare complete line of output
                        role_ip_info = '{0}\t\t{1}\t\t{2}\n\n'.format(str(inst['private_ip_address']), instance_role_name, stackname)

                        # accumulate stack output
                        stack_output += role_ip_info
            else:
                # accumulate stack output
                stack_output += '\n\nWARNING: Stack "{0}" Status is "{1}" - no IP info \n'.format(
                    stackname, stack_status)

            # accumulate service output
            service_output = service_output + stack_output

        # prepare results
        self.result.output = service_output.strip()
        self.result.format = skytask.output_format_raw
        return self.result

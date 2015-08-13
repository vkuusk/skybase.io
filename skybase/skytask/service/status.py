import logging

from skybase.skytask import SkyTask
from skybase.planet import Planet
from skybase.utils.logger import Logger
from skybase import skytask
from skybase.actions.dbstate import PlanetStateQueryTypes, PlanetStateDbQuery
from skybase.actions.skycloud import call_cloud_api

def service_status_add_arguments(parser):

    parser.add_argument(
        '-p', '--planet',
        dest='planet_name',
        action='store',
        help='planet name')

    parser.add_argument(
        '-s', '--service',
        dest='service_name',
        action='store',
        help='service name.')

    parser.add_argument(
        '-t', '--tag',
        dest='tag',
        action='store',
        help='deployment tag or continent.')

    parser.add_argument(
        '-i','--id',
        dest='skybase_id',
        action='store',
        default=None,
        help='SkybaseID of the service instantiation inside a planet/continent. format of id is a "/" separated string'
    )

    parser.add_argument(
        '-k', '--stack-name',
        dest='stack_name',
        action='store',
        help='single stack name.')

    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )

    parser.add_argument(
        '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        help='retrieve information for instances'
    )

class Status(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        self.logger = Logger(logging.getLogger(__name__), logging.INFO)
        self.name = 'service.status'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def preflight_check(self):
        return self.preflight_check_result

    def execute(self):
        # unpack args
        skybase_id = self.args.get('skybase_id')
        planet_name = self.args.get('planet_name')
        service_name = self.args.get('service_name')
        continent_tag = self.args.get('tag')
        stack_name = self.args.get('stack_name')
        verbose = self.args.get('verbose')

        # test if any query filtering args are provided to drive type of query
        no_query_args = skybase_id == planet_name == service_name == continent_tag == stack_name == None

        # initialize service status query
        if no_query_args:
            # no query filter args provided; limit output to planet list
            query = PlanetStateDbQuery(
                planet=planet_name,
                service=service_name,
                tag=continent_tag,
                stack=stack_name,
                query_type=PlanetStateQueryTypes.DRILLDOWN,
            )
        elif skybase_id:
            # query by unique skybase id
            query = PlanetStateDbQuery.init_from_id(skybase_id,)
        else:
            # query by provided arguments
            query = PlanetStateDbQuery(
                planet=planet_name,
                service=service_name,
                tag=continent_tag,
                stack=stack_name,
                query_type=PlanetStateQueryTypes.WILDCARD,
            )

        # execute query and return standard result
        query_result = query.format_result_set(query.execute())


        # extend query results if working with skybase ID or filter args that return stacks
        if not no_query_args:
            for result in query_result:
                # unpack query result
                recid, info = result.items()[0]
                stackname = info['cloud']['stack_name']

                # TODO: performance / DRY enhancement: register planet and only init when not present
                planet_name = recid.split('/')[1]
                planet = Planet(planet_name)

                # get stack status
                try:
                    stack_status = call_cloud_api(
                            planet=planet,
                            stack_name=stackname,
                            action='get_stack_status',
                    )
                except Exception as e:
                    stack_status = e.message

                # add skybase ID
                info['skybase_id'] = recid

                # add status to results
                info['cloud'].update({'stack_status': stack_status})

                # query cloud provider for current state information
                if verbose and stack_status == 'CREATE_COMPLETE':
                    instance_info = call_cloud_api(
                        planet=planet,
                        stack_name=stackname,
                        action='get_instance_info',
                    )
                    # insert roles info into query result object
                    info['roles'] = instance_info

        # execute query
        self.result.output = query_result
        self.result.format = skytask.output_format_json
        return self.result

import os
import glob
import errno
import shutil

import yaml

from skybase import config as sky_cfg

from skybase.utils import mkdir_path, basic_timestamp
from skybase.planet import Planet
from skybase.utils import simple_error_format
import skybase.actions.skycloud
import skybase.exceptions


class PlanetStateDb(object):
    def __init__(self, db=None, archive=None, resources=None, runner_cfg=None):

        if runner_cfg:
            self.runner_cfg = runner_cfg
        else:
            # initialize runner config from default if not provided
            self.runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)

        self.db = db if db else self.runner_cfg.data['service_state']['db']
        self.archive = archive if archive else self.runner_cfg.data['service_state']['archive']
        self.resources = resources if resources else self.runner_cfg.data['service_state']['resources']

class PlanetStateQueryTypes(object):
    DEPTH = 'depth'
    DRILLDOWN = 'drilldown'
    WILDCARD = 'wildcard'
    EXACT = 'exact'

class PlanetStateRecord(object):
    def __init__(self, recid, cloud=None):
        self.id = recid
        self.cloud = cloud

class PlanetStateCloudRecord(object):
    def __init__(self, recid, stack_id=None, stack_name=None):
        self.id = recid
        self.stack_id = stack_id
        self.stack_name = stack_name

    def get_cloud_info(self):
        cloud_info = vars(self)
        cloud_info.pop('id')
        return {'cloud': cloud_info}


class PlanetStateDbQuery(PlanetStateDb, PlanetStateQueryTypes):
    def __init__(self, planet=None, service=None, tag=None, stack=None, query_type=PlanetStateQueryTypes.WILDCARD):
        super(PlanetStateDbQuery, self).__init__()
        self.planet = planet
        self.service = service
        self.tag = tag
        self.stack = stack
        self.query_type = query_type
        self.query = self.make_query()

    @classmethod
    def init_from_id(cls, id, query_type=PlanetStateQueryTypes.EXACT):
        '''
        split query args on '/' and instantiate class with/out stack element
        expectation is that elements of id agree with positional arguments to class
        examples:
            /dev-os-sjc1-1/serviceX/0.0.1/12345/MTW0501-LOCAL-00/galacticEmpire
            /dev-os-sjc1-1/serviceX/0.0.1/12345/MTW0501-LOCAL-00
        query_type default as EXACT anticipating service.(delete|record|read\update)
        query_type WILDCARD can be used as short-hand for option in service.get-ips
        '''
        query_args = id.split('/')[1:]
        return cls(*query_args, query_type=query_type)


    def _get_query_depth(self):
        if self.query_type == self.EXACT:
            query_depth = len(self.query[len(self.db):].split('/')) - 1
        else:
            query_depth = len(self.query[len(self.db):].split('/')) - 2
        return query_depth

    def _order_query_args(self):
        # order query args into planet state DB hierarchy
        query_args = [self.planet,
                      self.service,
                      self.tag,
                      self.stack]
        return query_args

    def _make_depth_query(self):
        # order query args into planet state DB hierarchy
        query_args = self._order_query_args()
        # initialize query with root of planet state db
        query = self.db

        # prune undefined criteria from tail of arg list
        while query_args and query_args[-1] is None:
            query_args.pop()

        # add ordered query criteria or wildcard to query if blank
        for attr in query_args:
            if attr:
                query = os.path.join(query, attr)
            else:
                query = os.path.join(query, '*')
        return query

    def _make_drilldown_query(self):
        # order query args into planet state DB hierarchy
        query_args = self._order_query_args()
        # initialize query with root of planet state db
        query = self.db

        # add ordered query criteria to query, stopping at first blank
        for attr in query_args:
            if attr:
                query = os.path.join(query, attr)
            else:
                break

        # append wildcard to view contents of next lower directory level
        query += '/*'
        return query

    def _make_exact_query(self):
        # order query args into planet state DB hierarchy
        query_args = self._order_query_args()
        # initialize query with root of planet state db
        query = self.db

        # add ordered query criteria to query, stopping at first blank
        for attr in query_args:
            if attr:
                query = os.path.join(query, attr)
            else:
                break
        return query

    def _make_wildcard_query(self):
        # order query args into planet state DB hierarchy
        query_args = self._order_query_args()
        # initialize query with root of planet state db
        query = self.db

        # add ordered query criteria or wildcard to query if blank
        for attr in query_args:
            if attr:
                query = os.path.join(query, attr)
            else:
                query = os.path.join(query, '*')

        # append wildcard to view contents of lowest directory level
        query += '/*'
        return query

    def _get_depth_result_set(self, query_results):
        response = self._prepare_result_set(query_results)
        return response

    def _get_drilldown_result_set(self, query_results):
        # return contents of resource files if at lowest level, else record ids
        response = dict()
        if len(self._order_query_args()) == self._get_query_depth():
            response = self._get_result_data(query_results)
        else:
            response = self._prepare_result_set(query_results)
        return response

    def _get_exact_result_set(self, query_results):
        return self._get_drilldown_result_set(query_results)

    def _get_wildcard_result_set(self, query_results):
        # return contents of resource files
        response = dict()
        response = self._get_result_data(query_results)
        return response

    def _prepare_result_set(self, query_results):
        # remove absolute path to state db from results
        result_set = []
        for record in query_results:
            result_set.append(PlanetStateRecord(recid=self._prepare_record_id(record)))
        return result_set

    def _prepare_record_id(self, record):
        return prepare_record_id(self.db, self.resources, record)

    def _get_result_data(self, record_set):
        result_set = []
        for record in record_set:
            recid = self._prepare_record_id(record)
            with open(os.path.join(record), 'r') as f:
                data = yaml.load(f)
                result_set.append(
                    PlanetStateRecord(
                        recid=recid,
                        cloud=PlanetStateCloudRecord(
                            recid=recid,
                            stack_id=data.get('cloud', {}).get('id'),
                            stack_name=data.get('cloud', {}).get('name'),
                        )
                    )
                )
        return result_set

    def make_query(self):
        # derive filesystem glob query by query type
        query_switch = {
            self.DEPTH: self._make_depth_query,
            self.DRILLDOWN: self._make_drilldown_query,
            self.EXACT: self._make_exact_query,
            self.WILDCARD: self._make_wildcard_query,
            }
        return query_switch[self.query_type]()

    def can_find_exact(self):
        return os.path.isdir(self.query)

    def show_query_path(self):
        return self._prepare_record_id(self.query)

    def execute_query(self):
        # return all contents matching query pattern
        if self.query_type == self.EXACT:
            try:
                listdir_results = os.listdir(self.query)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise e
                else:
                    listdir_results = []
            query_results = [os.path.join(self.query, item) for item in listdir_results]
        else:
            query_results = glob.glob(self.query)
        return query_results

    def get_result_set(self, query_results):
        # produce results by query type based upon records ids found from query
        result_set_switch = {
            self.DEPTH: self._get_depth_result_set,
            self.DRILLDOWN: self._get_drilldown_result_set,
            self.EXACT: self._get_exact_result_set,
            self.WILDCARD: self._get_wildcard_result_set,
            }
        return result_set_switch[self.query_type](query_results)

    # TODO: DECISION: should formatting be left to calling module (planet state)
    def format_result_set(self, result_set):
        formatted_result_set = []
        for record in result_set:
            if record.cloud:
                formatted_result_set.append({record.id: record.cloud.get_cloud_info()})
            else:
                formatted_result_set.append(record.id)
        return formatted_result_set

    def execute(self):
        # convenience method to execute query and provide results
        return self.get_result_set(self.execute_query())

    def count(self):
        # convenience method to execute query and provide results
        return len(self.execute_query())

    def execount(self):
        result_set = self.execute()
        return (result_set, len(result_set))


def prepare_record_id(db, resources, record):
    spos = len(db)
    if record.find(resources) > 0:
        epos = record.find(resources) - 1
        return record[spos:epos]
    else:
        return record[spos:]


def write_service_state_record(planet_name, service_name, tag, registration, provider, stacks):

    from skybase.service.state import ServiceRegistryMetadata, ServiceRegistryBlueprint, ServiceRegistryLog

    # connect to database
    db = PlanetStateDb()

    # define record format as list of directory names based on deployment
    planetdb_basepath = os.path.join(
        db.db,
        planet_name,
        service_name,
        tag,
    )

    response = dict()

    # make unique service directory and write service information to files
    mkdir_path(planetdb_basepath)

    # write service metadata (manifest + artiball source)
    metadata_path = os.path.join(planetdb_basepath, ServiceRegistryMetadata.FILENAME)
    with open(metadata_path, 'w') as f:
        f.write(yaml.safe_dump(registration.get('metadata'), default_flow_style=False))

    # write original main deployment yaml contents as 'blueprint'
    blueprint_path = os.path.join(planetdb_basepath, ServiceRegistryBlueprint.FILENAME)
    with open(blueprint_path, 'w') as f:
        f.write(yaml.safe_dump(registration.get('blueprint'), default_flow_style=False))

    # write first log entry with deployment details
    log_path = os.path.join(planetdb_basepath, ServiceRegistryLog.FILENAME)

    with open(log_path, 'a') as service_log:

        # create planet state record for each stack in db
        for stack_name, stack_info in stacks.items():

            # create unique path
            planetdb_stack_path = os.path.join(planetdb_basepath, stack_name)

            # make unique stack directory
            mkdir_path(planetdb_stack_path)

            # create planet state DB record filename
            planetdb_record = os.path.join(
                planetdb_stack_path, db.resources
            )

            # template for cloud resource file contents
            cloud_resource = {
                'cloud': {
                    'provider': provider,
                }
            }

            # merge stack information into template
            cloud_resource['cloud'].update(stack_info)

            # write stack launch information to resource file
            with open(planetdb_record, 'w') as f:
                f.write(yaml.safe_dump(
                    cloud_resource,
                    default_flow_style=False))

            # planet state response points to file
            response[stack_name] = prepare_record_id(db.db, db.resources, planetdb_record)

            # write service log entry for stack deployment
            service_log.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\n'.format(
                basic_timestamp(),
                'DEPLOY',
                service_name,
                registration.get('metadata', {}).get('app_version'),
                registration.get('metadata', {}).get('build_id'),
                tag,
                stack_info['name'],
                registration.get('metadata', {}).get('source_artiball')))

    return response

def delete_stacks(planet_name, service_name, tag, stacks, apply):

    from skybase.service.state import ServiceRegistryLog

    result = dict()
    result['archive'] = []
    result['stack_status'] = dict()

    if not apply:
        result = {
            'delete_stacks': {
                'planet_name': planet_name,
                'stacks': stacks,
                'apply': apply,
            }
        }
    else:
        # acquire planet state db and connection to cloud provider
        db = PlanetStateDb()

        # define record format as list of directory names based on deployment
        planetdb_basepath = os.path.join(
            db.db,
            planet_name,
            service_name,
            tag,
        )

        # write first log entry with deployment details
        log_path = os.path.join(planetdb_basepath, ServiceRegistryLog.FILENAME)

        with open(log_path, 'a') as service_log:

            for recid, stack_info in stacks.items():
                # unpack stack_info
                stack_id = stack_info.get('stack_id')
                stack_launch_name = stack_info.get('stack_name')

                # verify cloud provider DELETE* status for stack id
                stack_status = skybase.actions.skycloud.call_cloud_api (
                    planet=Planet(planet_name),
                    stack_name=stack_id,
                    action='get_stack_status')

                result['stack_status'][stack_id] = stack_status
                if not stack_status.startswith('DELETE'):
                    continue

                # identify record source and archive destination
                src = os.path.join(db.db, recid.strip('/'))
                dst = os.path.join(db.archive, recid.strip('/'))

                # identify resources file
                srcfile = os.path.join(src, db.resources)
                dstfile = os.path.join(dst, db.resources)

                # make archive folder path
                skybase.utils.mkdir_path(dst)
                shutil.move(srcfile, dstfile)
                result['archive'].append(recid)

                # clean-up non-empty planet registry directory tree from bottom to top
                while recid:
                    # join database and key
                    target_dir = os.path.join(db.db, recid.strip('/'))

                    # attempt to remove bottom stack path directory
                    # discontinue if not empty of file or other directory
                    try:
                        os.rmdir(target_dir)
                    except OSError:
                        if errno.ENOTEMPTY:
                            break
                        else:
                            raise

                    # remove last element of stack path
                    tempdir = recid.split(os.path.sep)
                    tempdir.pop()
                    recid = os.path.sep.join(tempdir)

                # DECISION: need globally/app available execution mode setting to be able to read from state db api. how?
                # TODO: need to acquire current service metadata from state db service.
                # write service log entry for stack deployment
                service_log.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\n'.format(
                    basic_timestamp(),
                    'DELETE',
                    service_name,
                    'TODO_METADATA_VERSION',
                    'TODO_METADATA_BUILD_ID',
                    tag,
                    stack_launch_name,
                    'TODO_METADATA_SOURCE_ARTIBALL'))

    return result
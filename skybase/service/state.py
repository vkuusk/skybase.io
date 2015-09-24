import yaml
import os

from skybase.actions.dbstate import PlanetStateDb
import skybase.exceptions
from skybase.utils import basic_timestamp, simple_error_format
from skybase.utils.schema import read_yaml_from_file
from skybase.actions.dbstate import PlanetStateDbQuery
from skybase.actions.skycloud import call_cloud_api
from skybase.planet import Planet

class ServiceRegistryRecord(object):
    def __init__(self, id, planet, service, tag, metadata, blueprint, log, stacks):
        self.id = id
        self.planet = planet
        self.service = service
        self.tag = tag
        self.metadata = metadata
        self.blueprint = blueprint
        self.log = log
        self.stacks = stacks

    @classmethod
    def init_from_id(cls, id):
        planet, service, tag = id.split('/')[1:]
        metadata = ServiceRegistryMetadata.init_from_id(id)
        blueprint = ServiceRegistryBlueprint.init_from_id(id)
        log = ServiceRegistryLog.init_from_id(id)
        stacks = ServiceRegistryStacks.init_from_id(id)
        return cls(id, planet, service, tag, metadata, blueprint, log, stacks)

    @property
    def salt_tgt(self):
        # prepare service scope minion targeting string
        salt_tgt = '-'.join([self.planet, self.service, self.tag]) + '*'
        return salt_tgt

    def output_as_dict(self):
        result = {
            'id': self.id,
            'planet': self.planet,
            'service': self.service,
            'tag': self.tag,
            'metadata': self.metadata.output_as_dict(),
            'blueprint': self.blueprint.output_as_dict(),
            'log': self.log.output_as_dict(),
            'stacks': self.stacks.output_as_dict()
        }
        return result

    def serialize_as_yaml(self):
        return yaml.dump(self)

    def update(self):
        try:
            self.metadata.update()
            self.blueprint.update()
            # TODO: COOKBOOK_ONLY first and only update type supported.  will eventually derive from --plan option and artiball config
            log_entry = '{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\n'.format(
                basic_timestamp(),
                'UPDATE_RERUN',
                self.service,
                self.metadata.version,
                self.metadata.build,
                self.tag,
                self.metadata.artiball,
            )
            self.log.update(log_entry)
            return True
        except Exception as e:
            return simple_error_format(e)


class ServiceRegistryMetadata(object):
    FILENAME = 'metadata.yaml'

    def __init__(self, id, name, version, build, artiball):
        self.id = id
        self.name = name
        self.version = version
        self.build = build
        self.artiball = artiball

    @property
    def record(self):
        db = PlanetStateDb()
        record = os.path.join(db.db, self.id.strip('/'), ServiceRegistryMetadata.FILENAME)
        return record

    @classmethod
    def init_from_id(cls, id):
        # connect to database
        db = PlanetStateDb()

        # prepare path to file and call init_from_file
        metadata_file = os.path.join(db.db, id.strip('/'),
                                     ServiceRegistryMetadata.FILENAME)

        return cls.init_from_file(id, metadata_file)

    @classmethod
    def init_from_file(cls, id, metadata_file):
        # attempt to read file contents
        try:
            metadata = read_yaml_from_file(metadata_file)
        except IOError:
            raise skybase.exceptions.StateDBRecordNotFoundError(id)
        else:
            # map file contents to values and call init
            name = metadata.get('app_name')
            version = metadata.get('app_version')
            build = metadata.get('build_id')
            artiball = metadata.get('source_artiball')

        return cls(id, name, version, build, artiball)

    def output_as_dict(self):
        result = {
            'id': self.id,
            'app_name': self.name,
            'app_version': self.version,
            'build_id': self.build,
            'source_artiball': self.artiball,
        }
        return result

    def update(self):
        with open(self.record, 'w') as f:
            f.write(yaml.safe_dump(self.output_as_dict(), default_flow_style=False))


class ServiceRegistryBlueprint(object):
    FILENAME = 'blueprint.yaml'

    def __init__(self, id, definition, stacks):
        self.id = id
        self.definition = definition
        self.stacks = stacks

    @property
    def record(self):
        db = PlanetStateDb()
        record = os.path.join(db.db, self.id.strip('/'), ServiceRegistryBlueprint.FILENAME)
        return record

    @classmethod
    def init_from_id(cls, id):
        # connect to database
        db = PlanetStateDb()

        # prepare path to file and call init_from_file
        blueprint_file = os.path.join(db.db, id.strip('/'), ServiceRegistryBlueprint.FILENAME)

        return cls.init_from_file(id, blueprint_file)

    @classmethod
    def init_from_file(cls, id, blueprint_file):
        # attempt to read file contents
        try:
            blueprint = read_yaml_from_file(blueprint_file)
        except IOError:
            raise skybase.exceptions.StateDBRecordNotFoundError(id)
        else:
            definition = blueprint.get('definition')
            stacks = blueprint.get('stacks')

        return cls(id, definition, stacks)

    def output_as_dict(self):
        result = {
            'id': self.id,
            'definition': self.definition,
            'stacks': self.stacks,
        }
        return result

    def update(self):
        # TODO: intentionally not overwriting blueprint; topology considered immutable from origin deployment (for now)
        pass

    def get_stack_roles(self, stack_name):
        return self.stacks[stack_name].get('roles', {}).keys()


class ServiceRegistryLog(object):
    FILENAME = 'service.log'

    def __init__(self, id, log):
        self.id = id
        self.log = log

    @property
    def record(self):
        db = PlanetStateDb()
        record = os.path.join(db.db, self.id.strip('/'), ServiceRegistryLog.FILENAME)
        return record

    @classmethod
    def init_from_id(cls, id):
        # connect to database
        db = PlanetStateDb()

        # prepare path to file and call init_from_file
        log_file = os.path.join(db.db, id.strip('/'), ServiceRegistryLog.FILENAME)

        return cls.init_from_file(id, log_file)

    @classmethod
    def init_from_file(cls, id, log_file):
        # attempt to log file contents and init class with results
        try:
            with open(log_file) as f:
                log = f.read().splitlines()
        except IOError:
            log = []

        return cls(id, log)

    def output_as_dict(self):
        result = {
            'id': self.id,
            'log': self.log,
        }
        return result

    def update(self, entry):
        with open(self.record, 'a') as f:
            f.write('{0}'.format(entry))

class ServiceRegistryStacks(object):
    def __init__(self, service_id, stacks):
        self.service_id = service_id
        self.stacks = stacks

    @property
    def record(self):
        db = PlanetStateDb()
        record = os.path.join(db.db, self.service_id.strip('/'))
        return record

    @property
    def deployed_stacks(self):
        return self.stacks.keys()

    @property
    def deployed_stacks_status(self):
        return {stack.stack_name: stack.get_stack_status() for stack in self.stacks}

    @classmethod
    def init_from_id(cls, service_id):
        # connect to database
        db = PlanetStateDb()

        # prepare path to file and call init_from_file
        service_path = os.path.join(db.db, service_id.strip('/'))

        # any/all subdirs to service are assumed to be a deployed stack
        try:
            deployed_stacks = [stack for stack in os.listdir(service_path)
                      if os.path.isdir(os.path.join(service_path, stack))]
        except OSError:
            deployed_stacks = []

        stacks = dict()
        for stack in deployed_stacks:
            service_stack_id = '/'.join([service_id, stack])
            stacks[stack] = ServiceRegistryStack.init_from_id(service_stack_id)

        return cls(service_id, stacks)

    def output_as_dict(self):
        result = {stacks_key: stack.output_as_dict() for stacks_key, stack in self.stacks.items()}
        return result

class ServiceRegistryStack(object):

    def __init__(self, service_id, stack_name, stack_info=None):
        self.service_id = service_id
        self.stack_name = stack_name
        self.stack_info = stack_info

    @property
    def record(self):
        db = PlanetStateDb()
        record = os.path.join(db.db, self.service_id.strip('/'), self.stack_name)
        return record

    @property
    def salt_grain_stack_base_tgt(self):
        # prepare service scope minion targeting string
        service_stack_attr = self.service_id.split('/')[1:]
        service_stack_attr.append(self.stack_name)
        salt_grain_stack_base_tgt = '-'.join(service_stack_attr)
        return salt_grain_stack_base_tgt

    @property
    def salt_grain_skybase_id(self):
        salt_grain_skybase_id = 'skybase:skybase_id:{0}*'.format(self.salt_grain_stack_base_tgt)
        return salt_grain_skybase_id

    def get_stack_role_salt_grain_skybase_id(self, role):
        salt_grain_skybase_stack_role_id = 'skybase:skybase_id:{0}-{1}'.format(self.salt_grain_stack_base_tgt, role)
        return salt_grain_skybase_stack_role_id

    @classmethod
    def init_from_id(cls, service_stack_id):
        # split service id into service and stack components
        service_id = os.path.dirname(service_stack_id)
        stack_name = os.path.basename(service_stack_id)

        # retrieve stack information
        query = PlanetStateDbQuery.init_from_id(service_stack_id)
        stack_info = query.format_result_set(query.execute())

        # initialize class using primary constructor
        return cls(service_id, stack_name, stack_info)

    def get_stack_status(self):
        # split service stack id into positional components
        planet_name = self.service_id.split('/')[1]

        # acquire provider stack status
        stack_status = None
        planet = Planet(planet_name)

        # TODO/DECISION: fail silently and let context determine action or raise errors?
        # attempt to acquire stack status
        try:
            stack_id = self.stack_info[0].values()[0]['cloud']['stack_id']
            stack_status = call_cloud_api(
                planet=planet,
                stack_name=stack_id,
                action='get_instance_info',
            )
        except Exception as e:
            pass

        return stack_status

    def output_as_dict(self):
        result = {
            'stack_name': self.stack_name,
            'stack_info': self.stack_info,
        }
        return result
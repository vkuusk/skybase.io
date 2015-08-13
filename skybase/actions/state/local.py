import string
import shelve
import time
import uuid
import os
import yaml

import skybase.config as sky_cfg
from skybase.service.state import ServiceRegistryRecord
from skybase.utils import mkdir_path

def create(planet_name, service_name, tag, registration, provider, stacks):
    # TODO: enable real work replacing record_id with emission from class
    # state_db_record = ServiceRegistryRecord()
    # state_db_record.create()
    record_id = os.path.join('/', planet_name, service_name, tag)
    return record_id

def read(record_id, format=None):
    '''
    attempt to instantiate state db record from id
    '''

    state_db_record = ServiceRegistryRecord.init_from_id(record_id)

    if format == 'yaml':
        result = state_db_record.serialize_as_yaml()
    else:
        result = state_db_record.output_as_dict()
    return result

def update(record_id, record_object, **kwargs):
    current_state_db_record = ServiceRegistryRecord.init_from_id(record_id)
    record_bi_key = create_bi_record(record_id, current_state_db_record)

    new_state_db_record = yaml.load(record_object)
    new_state_db_record.update()

    result = {
        'record_id': record_id,
        'record_bi_key': record_bi_key,
    }

    return result

#TODO: rename to get_bi for clarity
def get_bi_db(config_dir=None):
    # require runner config
    if not config_dir: config_dir = sky_cfg.CONFIG_DIR
    runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=config_dir)

    # find service state before image object store
    service_state_bi_dir = runner_cfg.data['service_state']['bi_dir']
    service_state_bi_file = runner_cfg.data['service_state']['bi_file']

    # DECISION-TODO: push path creation into role so that path existence is guaranteed
    # idempotently make BI directory path if not exists
    mkdir_path(service_state_bi_dir)

    # prepare bi database file fullpath
    service_state_bi = os.path.join(service_state_bi_dir, service_state_bi_file)

    return service_state_bi

def create_bi_record(record_id, record_object):
    # DECISION: should before image key be emitted from record_object method?
    ts = int(time.time())
    record_bi_key = '{0}.{1}.{2}'.format(string.replace(record_id.strip('/'), '/', '.'), ts, uuid.uuid4())

    # stash before image of service registry object
    db = shelve.open(get_bi_db())
    # TODO: add skybase app version to record for backwards compatibility in reconstituting records
    db[record_bi_key] = {
        'id': record_bi_key,
        'record': record_object,
        'timestamp': ts,
        'record_id': record_id,
    }
    db.close()

    return record_bi_key

def read_bi_record(record_bi_key):
    db = shelve.open(get_bi_db())
    record_object = db.get(record_bi_key)
    db.close()
    return record_object


from . import local
from . import restapi

def create(mode, planet_name, service_name, tag, registration, provider, stacks, credentials=None):
    '''
    execute state db read action based on modality: local or restapi
    '''

    result = dict()

    if mode == 'restapi':
        result = restapi.create(planet_name, service_name, tag, registration, provider, stacks, credentials)

    elif mode == 'local':
        # attempt to read from state db locally/directly
        result = local.create(planet_name, service_name, tag, registration, provider, stacks)

    return result



def read(mode, record_id, credentials=None, format=None):
    '''
    execute state db read action based on modality: local or restapi
    '''

    result = dict()

    if mode == 'restapi':
        result = restapi.read(record_id, credentials, format)

    elif mode == 'local':
        # attempt to read from state db locally/directly
        result = local.read(record_id, format=format)

    return result

def update(mode, record_id, service_record, credentials=None):
    '''
    execute state db read action based on modality: local or restapi
    '''

    result = dict()

    if mode == 'restapi':
        result = restapi.update(record_id, service_record, credentials)

    elif mode == 'local':
        # attempt to read from state db locally/directly
        result = local.update(record_id, service_record)

    return result

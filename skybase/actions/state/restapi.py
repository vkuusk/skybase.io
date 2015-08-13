import skybase.api.state
import skybase.exceptions

def create(planet_name, service_name, tag, registration, provider, stacks, credentials=None):
    response = skybase.api.state.create(
        planet_name,
        service_name,
        tag,
        registration,
        provider,
        stacks,
        credentials
    )
    result = response.json().get('data', {})
    return result

def read(id, credentials, format=None):
    response = skybase.api.state.read(
        record_id=id,
        credentials=credentials,
        format=format,
    )

    # TODO: examine response status (200, non-200) and header (json, plain-text) to determine handling
    # DECISION/TODO: reconstitute and reraise skybase/statedb errors
    result = response.json().get('data', {})
    return result

def update(record_id, service_record, credentials):
    response = skybase.api.state.update(
        record_id=record_id,
        service_record=service_record,
        credentials=credentials,
    )

    result = response.json().get('data', {})
    return result

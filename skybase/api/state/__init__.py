import urllib
import os
import json

from ...api import create_api_url, create_auth_http_headers, submit_http_request


def create(planet_name, service_name, tag, registration, provider, stacks, credentials):

    record_id = os.path.join('/', planet_name, service_name, tag)

    # create URL to state record id
    url = create_api_url(route='state{0}'.format(record_id))

    data = json.dumps({
        'planet_name': planet_name,
        'service_name': service_name,
        'tag': tag,
        'registration': registration,
        'provider': provider,
        'stacks': stacks
    })

    headers = create_auth_http_headers(credentials, data)

    # prepare request and submit
    response = submit_http_request(
        method='POST',
        url=url,
        headers=headers,
        data=data,
    )

    return response

def read(record_id, credentials, format=None):
    # create URL to state record id
    url = create_api_url(route='state{0}'.format(record_id))

    # DECISION: GET request without data will have identical signatures; need method for injecting entropy
    headers = create_auth_http_headers(credentials)

    # TODO: create utility to prepare and accumlate 0-N query string pairs
    # provide params as query string
    params = dict()
    if format:
        qs_pairs = {'format': format}
        params = urllib.urlencode(qs_pairs)

    # prepare request and submit
    response = submit_http_request(
        method='GET',
        url=url,
        headers=headers,
        params=params,
    )

    return response

def update(record_id, service_record, credentials):
    # create URL to state record id
    url = create_api_url(route='state{0}'.format(record_id))

    data = service_record

    headers = create_auth_http_headers(credentials, data)

    # prepare request and submit
    response = submit_http_request(
        method='PUT',
        url=url,
        headers=headers,
        data=data,
    )

    return response

def delete(id):
    pass
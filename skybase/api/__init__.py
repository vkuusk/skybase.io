import json
import hmac
import hashlib
import base64

import requests

from skybase import config as sky_cfg
import skybase.utils
import skybase.exceptions


def create_signature(key, message):
    h = hmac.new(bytearray(key, 'UTF-8'), msg=str(message), digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(h).decode()
    return signature

def check_signature(key, message, signature):
    check_signature = create_signature(key, message)
    result = (check_signature == signature)
    return result

def get_api_server():
    runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)

    # attempt to access restapi server url
    restapi_server_url = runner_cfg.data.get('restapi_server_url')

    # use default value in config value if not found or empty
    if restapi_server_url is None:
        restapi_server_url = sky_cfg.API_SERVER

    return restapi_server_url

def create_api_url(
        server=None,
        root=sky_cfg.API_ROOT,
        version=sky_cfg.API_VERSION,
        route=''):

    # TODO: can't make get_api_server() default as it attempts to read in configs before CLI values passed
    if server is None:
        server = get_api_server()

    # assemble url
    url = '/'.join([server, root, version, route])

    return url

def create_auth_http_headers(credentials, data=''):
    # sign data request body with user credentials
    request_signature = skybase.api.create_signature(credentials.get('key'), data)

    # prepare request header
    headers = {
        sky_cfg.API_HTTP_HEADER_ACCESS_KEY: credentials.get('user_id'),
        sky_cfg.API_HTTP_HEADER_SIGNATURE: request_signature,
    }
    return headers

def submit_http_request(method, url, **kwargs):
    # request to skybase http services
    try:
        response = requests.request(
            method=method,
            url=url,
            **kwargs
        )
    except requests.exceptions.ConnectionError as e:
        raise skybase.exceptions.SkyBaseRestAPIError(skybase.utils.simple_error_format(e))

    return response


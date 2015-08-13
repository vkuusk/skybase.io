import socket
import time

from skybase import config as sky_cfg
from skybase.utils import basic_timestamp


def ping(**kwargs):
    start_time = time.time()
    time.sleep(float(kwargs.get('sleep_interval', 0)))

    response = {
        'data': {
            'planet': kwargs.get('planet_name'),
            'hostname': socket.gethostname(),
            'sleep_interval': float(kwargs.get('sleep_interval')),
            'work_in_secs': time.time() - start_time,
            'timestamp': basic_timestamp(),
        },
        'status': sky_cfg.API_STATUS_SUCCESS,
    }

    return response

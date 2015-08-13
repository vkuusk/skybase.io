import json

from skybase import config as sky_cfg
from skybase.api import submit_http_request
from skybase.planet import Planet

# TODO: push base functionality into SaltAPIBase(); Subclass for Skybase and add specifics;
class SkySaltAPI(object):

    NO_MINIONS = 'No minions matched the target. No command was sent, no jid was assigned.'

    def __init__(self, planet_name=None, url=None, username=None, password=None, authtoken = None, runner_cfg=None):
        if runner_cfg:
            self.runner_cfg = runner_cfg
        else:
            self.runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)

        '''
        TODO: workaround to go resolve api through planet until salt(master + syndic + api) bug is fixed
        reference: https://github.com/saltstack/salt/issues/9141
        '''
        # select api url from argument, derive from planet, or config master of masters
        if url:
            self.url = url
        elif planet_name:
            self.url = Planet(planet_name).services['salt']['api']['url']
        else:
            self.url = self.runner_cfg.data['salt']['api']['url']

        self.username = username
        self.password = password
        self.authtoken = authtoken

    @property
    def login(self):
        return '{0}/login'.format(self.url)

    @property
    def run(self):
        return '{0}/run'.format(self.url)

    @property
    def minions(self):
        return '{0}/minions'.format(self.url)

    @property
    def jobs(self):
        return '{0}/jobs'.format(self.url)

    @property
    def endpoints(self):
        endpoints = {
            'login': self.login,
            'run': self.run,
            'minions': self.minions,
            'jobs': self.jobs,
        }
        return endpoints

    def get_authtoken(self, username, password):
        status, response = self.submit_login_request(username, password)
        authtoken = None
        if status < 400:
            authtoken = response['return'][0]['token']
        return authtoken

    def authorize(self, username=None, password=None):
        self.username = username if username else self.username
        self.password = password if password else self.password
        self.authtoken = self.get_authtoken(self.username, self.password)

    def is_authorized(self):
        return self.authtoken is not None

    def submit_login_request(self, username, password):
        data = {
            'username': username,
            'password': password,
            'eauth': 'pam',
        }

        request = submit_http_request(
            method='POST',
            url=self.login,
            data=data,
            verify=False,
        )

        if request.status_code < 400:
            response = request.json()
        else:
            response = json.dumps(request.content)

        return request.status_code, response

    def submit_minions_request(self, minion_id):
        headers = {
            'X-Auth-Token': self.authtoken,
        }

        request = submit_http_request(
            method='GET',
            url='{0}/{1}'.format(self.minions, minion_id),
            headers=headers,
            verify=False,
        )

        if request.status_code < 400:
            response = request.json()
        else:
            response = json.dumps(request.content)

        return request.status_code, response

    def submit_jobs_request(self, job_id):
        headers = {
            'X-Auth-Token': self.authtoken,
        }

        request = submit_http_request(
            method='GET',
            url='{0}/{1}'.format(self.jobs, job_id),
            headers=headers,
            verify=False,
        )

        if request.status_code < 400:
            response = request.json()
        else:
            response = json.dumps(request.content)

        return request.status_code, response

    def submit_run_request(self, tgt='*', fun='', client='local_async', arg=[], expr_form='glob', **kwargs):
        # prepare request data
        data = {
            'tgt': tgt,
            'fun': fun,
            'arg': arg,
            'client': client,
            'expr_form': expr_form,
        }
        data.update(kwargs)

        # sign request
        headers = {
            'X-Auth-Token': self.authtoken,
        }

        request = submit_http_request(
            method='POST',
            url=self.run,
            headers=headers,
            data=data,
            verify=False,
        )

        if request.status_code < 400:
            response = request.json()
        else:
            response = json.dumps(request.content)

        return request.status_code, response

    def test_ping(self, tgt='*', client='local', **kwargs):
        response = self.submit_run_request(tgt=tgt, fun='test.ping', client=client, **kwargs)
        return response

    def grains_item(self, tgt='*', *args):
        response = self.submit_run_request(tgt, 'grains.item', *args)
        return response

    def cmd_run(self, tgt=None, client='local_async', arg=[], **kwargs):
        response = self.submit_run_request(tgt=tgt, client=client, fun='cmd.run', arg=arg, **kwargs)
        return response

    def update_service(self, tgt=None, action=None, client='local_async'):
        response = self.cmd_run(
            tgt=tgt,
            client=client,
            arg=[action,],
            expr_form='grain',
        )
        return response



import json
import time
import logging

import requests
import requests.exceptions

from skybase.parser import parse_skycmd_argv
from skybase import runner as sky_runner
from skybase import config as sky_cfg
from skybase.utils import simple_error_format, json_pretty_print
import skybase.api
import skybase.skytask
from skybase.exceptions import SkyBaseError, SkyBaseResponseError, SkyBaseTimeOutError, SkyBaseRestAPIError, SkyBasePresubmitCheckError


# brute force and crude suppression annoying INFO:requests.package logging message
logging.getLogger("requests").setLevel(logging.WARNING)


class SkyCmd(object):
    # constants / defaults used when polling for results
    TIMEOUT_DEFAULT = 60
    TIMEOUT_MAX = 300
    RETRY = 2

    def __init__(self):

        # initialize Cmd structure:
        self.args = self.process_args()

        # convert dashes into underscores in group and command
        self.group_name = '_'.join(self.args.command_group.split('-'))
        self.command_name = '_'.join(self.args.command_name.split('-'))

        # TODO: formulation of task name better as method for reuse
        self.current_task_name = '.'.join([self.group_name, self.command_name])

        # acquire client config using dir provided as CLI option or default
        self.cli_cfg = sky_cfg.SkyConfig.init_from_file('client', config_dir=self.args.config_dir)

    def process_args(self):

        all_args = parse_skycmd_argv()
        # some processing

        # return resulting args
        return all_args

    def run(self):
        '''
        For the record:

        set mode:
        a) restapi = submit, get JobID, forget                      = task is sent away
        b) local.sync = do something local in sync mode             = task has actions executed local
        c) local.async.wait = submit, get jobID, go into WAIT loop  = task submitted, but reply has to be reported back to cli
        d) local.async.nowait = submit, get jobID, forget           = task executed locally, but no wait for systems outside SB
        '''

        # Do a quick & dirty presubmit check. This is meant for allowing a
        # simple 'yes/no' or 'are you sure' type verification check
        try:
            precheck_runner = sky_runner.Runner(self.current_task_name, vars(self.args))
            precheck_runner.task.presubmit_check()
        except SkyBasePresubmitCheckError as e:
            raise e
        except Exception:
            pass

        if self.args.exec_mode == 'local':
            # call runner for current skytask with arguments
            runner = sky_runner.Runner(self.current_task_name, vars(self.args))

            # init results containers
            result_main = None
            result_next = None

            try:
                result_main = runner.execute()
            except Exception as e:
                raise SkyBaseResponseError('{0} when accessing execution results'.format(simple_error_format(e)))

            has_next_task = len(result_main.next_task_name) > 0

            if has_next_task:
                runner = sky_runner.Runner(result_main.next_task_name, result_main.next_args)
                try:
                    result_next = runner.execute()
                except Exception as e:
                    raise SkyBaseResponseError('{0} when accessing execution results'.format(simple_error_format(e)))

            if result_main.format == skybase.skytask.output_format_json:
                if has_next_task:
                    # prepare multiple result for output as single JSON blob
                    summary_result = []
                    summary_result.append({self.current_task_name: result_main.output})
                    summary_result.append({result_main.next_task_name: result_next.output})
                    print skybase.utils.json_pretty_print(summary_result)
                else:
                    # print main results separately
                    result_main.print_result()
            else:
                # print results separately
                result_main.print_result()
                if has_next_task:
                    result_next.print_result()

        elif self.args.exec_mode == 'restapi':
            response = self.submit()

            if self.args.nowait:
                print response
            else:
                # deserialize request response
                response_as_json = json.loads(response)

                # check restapi status; if success, attempt to extract results
                if response_as_json.get('status') == sky_cfg.API_STATUS_SUCCESS:
                    result = self.get_restapi_execute_result(response_as_json)
                    taskresult = skybase.skytask.TaskResult.init_from_json(result)
                else:
                    # ... if not success, report message containing error
                    taskresult = skybase.skytask.TaskResult(
                        an_output=response_as_json.get('message'),
                        a_format=skybase.skytask.output_format_json,
                    )
                taskresult.print_result()

    def submit(self):
        # acquire user credentials
        self.sky_credentials = sky_cfg.SkyConfig.init_from_file('credentials', config_dir=self.args.creds_dir)

        req = self.submit_http_request()
        response = req.content

        return response

    def submit_http_request(self):
        # prepare request data/body
        data = {
            'args': vars(self.args),
            'metadata': self.prepare_job_metadata()
        }

        # sign data request body with user credentials
        request_signature = skybase.api.create_signature(self.sky_credentials.data['key'], json.dumps(data))

        # prepare request header
        headers = {
            sky_cfg.API_HTTP_HEADER_ACCESS_KEY: self.sky_credentials.data['user_id'],
            sky_cfg.API_HTTP_HEADER_SIGNATURE: request_signature,
        }

        # get default restapi task url
        restapi_url = skybase.api.create_api_url(
            server=self.cli_cfg.get_data_value('restapi_server_url', data_default=sky_cfg.API_SERVER),
            route=sky_cfg.API_ROUTES.get('task'),
        )

        # gather query parameter string
        params = self.get_request_params()

        # post request to restapi
        try:
            response = requests.post(
                restapi_url,
                params=params,
                headers=headers,
                data=json.dumps(data),
            )
        except requests.exceptions.ConnectionError as e:
            raise SkyBaseRestAPIError(simple_error_format(e))

        return response

    def prepare_job_metadata(self):
        metadata = {
            'current_task_name': self.current_task_name,
            'timestamp': skybase.utils.basic_timestamp(),
            'user_id': self.sky_credentials.data['user_id']
        }
        return metadata

    def get_request_params(self):
        # prepare query parameter string using required/expected key=value pairs
        group = '='.join(['group', self.group_name])
        command = '='.join(['command', self.command_name])

        # TODO: revise all group.commands using --planet arg dest='planet_name'
        # inspect args for --planet option
        planet_param = None
        if 'planet_name' in self.args and self.args.planet_name:
            planet_param = '='.join(['planet', self.args.planet_name])
        elif 'destination_planet' in self.args and self.args.destination_planet:
            planet_param = '='.join(['planet', self.args.destination_planet])
        elif 'planet' in self.args and self.args.planet:
            planet_param = '='.join(['planet', self.args.planet])

        # create url query parameter string
        if planet_param:
            params = "&".join([group, command, planet_param])
        else:
            params = "&".join([group, command])
        return params

    def probe(self, url):
        # attempt to retrieve url
        response = requests.get(url)
        result = json.loads(response.content)
        return result

    def pollwait(self,
                 url,
                 timeout=None,
                 retry_interval=RETRY):

        if timeout is None:
            timeout = min(self.cli_cfg.data.get('result_fetch_timeout', SkyCmd.TIMEOUT_DEFAULT), SkyCmd.TIMEOUT_MAX)

        # wait for celery task status SUCCESS over timeout interval
        start_time = time.time()

        while time.time() - start_time < timeout:
            execute_result = self.probe(url)

            try:
                status = execute_result['metadata']['task_status']
            except KeyError as e:
                raise SkyBaseResponseError('{0} when accessing response status'.format(simple_error_format(e)))

            if status == 'PENDING':
                # TODO: progress bar would be nice, but needs to not interfere with json prettyprint
                time.sleep(retry_interval)

            elif status == 'SUCCESS':
                # return execute task results data if exists
                try:
                    return execute_result
                except KeyError as e:
                    raise SkyBaseResponseError('{0} when accessing response results'.format(simple_error_format(e)))
            else:
                raise SkyBaseError('unknown task status: {0}'.format(status))

        raise SkyBaseTimeOutError('attempt to fetch results failed after {0}s'.format(timeout))

    def get_restapi_execute_result(self, response):
        # extract results from backend db using execution link in response
        try:
            # result = self.pollwait(json.loads(response)['links']['result']['href'])
            result = self.pollwait(response['links']['result']['href'])
            result_data = result['data']
            return result_data
        except Exception as e:
            raise SkyBaseResponseError('{0} when accessing execution results'.format(simple_error_format(e)))

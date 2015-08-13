import os
import sys
import inspect
import argparse
import logging
import json
from functools import wraps

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.escape
from tornado.log import enable_pretty_logging

import skybase.worker.celery.tasks
import skybase.worker.celery.state.tasks
import skybase.exceptions
import skybase.utils
import skybase.skymap
import skybase.api
import skybase.actions.auth.db
from skybase import config as sky_cfg
import skybase.actions.state.local


tornado_access_log = logging.getLogger("tornado.access")

end_point_paths = {}

# TODO: move into separate module after debug, dev, &c.
class SkyResponse(object):
    def __init__(self, code=None, status=None, data=None, links=None,
                 metadata=None, message=None):
        self.code = code
        self.status = status
        self.data = data
        self.links = links
        self.metadata = metadata
        self.message = message

    @property
    def response(self):
        response = {
            'code': self.code,
            'status': self.status,
            'data': self.data,
            'links': self.links,
            'metadata': self.metadata,
            'message': self.message
        }
        return response


def make_error_response(code, error):
    response = SkyResponse()
    tornado_access_log.warning(skybase.utils.simple_error_format(error))
    response.message = skybase.utils.simple_error_format(error)
    response.code = code
    response.status = sky_cfg.API_STATUS_FAIL
    return response.response


def authenticated(method):
    '''
    request handler method decorator to authenticate request
    :param method:
    :return:
    '''
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        tornado_access_log.debug('authenticating request: {0} {1} request'.format(self.__class__.__name__, self.request.method))

        # capture header values used by authentication
        access_key = self.request.headers.get(sky_cfg.API_HTTP_HEADER_ACCESS_KEY)
        request_signature = self.request.headers.get(sky_cfg.API_HTTP_HEADER_SIGNATURE)

        # required auth_id and signature
        if not (request_signature and access_key):
            # create error response
            errmsg = '{0}={1}; {2}={3}'.format(
                        sky_cfg.API_HTTP_HEADER_ACCESS_KEY, access_key,
                        sky_cfg.API_HTTP_HEADER_SIGNATURE, request_signature)
            self.set_status(403)
            self.write(make_error_response(
                self.get_status(),
                skybase.exceptions.SkyBaseAuthenticationError(errmsg)))
            self.finish()
            return

        # lookup secret key paired with authentication key from db
        try:
            tornado_access_log.debug('attempt lookup secret key for {0}'.format(access_key))
            secret_key = skybase.actions.auth.db.lookup_key(access_key)
        except skybase.exceptions.SkyBaseError as e:
            # create error response
            tornado_access_log.debug('failed lookup secret key for {0}'.format(access_key))
            self.set_status(403)
            errmsg = make_error_response(self.get_status(), e)
            self.write(errmsg)
            self.finish()
            return

        # compare request signature against freshly signed body
        tornado_access_log.debug('request.body: {0}'.format(self.request.body))
        is_authenticated = skybase.api.check_signature(
            secret_key,
            self.request.body,
            request_signature)

        if is_authenticated:
            return method(self, *args, **kwargs)
        else:
            self.set_status(403)
            errmsg = make_error_response(
                self.get_status(),
                skybase.exceptions.SkyBaseAuthenticationError(
                    'message signature mismatch'))
            self.write(errmsg)
            self.finish()
            return

    return wrapper


class SkyRestAPI(object):
    def __init__(self):

        # get the options from command line
        # Note: Configs are parsed by SkyConfig and available as "sky_cfg"
        self.parse_options()

        # create list of end points and handlers
        end_point_list = []

        clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)

        for name, obj in clsmembers:
            if obj.__bases__[0].__name__ == 'RequestHandler':
                end_point_list.append(tuple([end_point_paths[name], obj]))

        # TODO: need tornado-based solution for changing log level
        tornado_access_log.setLevel(self.log_level.upper())

        rest_cfg = sky_cfg.SkyConfig.init_from_file('restapi', config_dir=sky_cfg.CONFIG_DIR)
        # Initialize the Application object
        # Add restapi config to application settings under skybase namespace
        # --config value read into global skybase config module
        self.application = tornado.web.Application(
            handlers=end_point_list,
            template_path=os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "templates"),
            static_path=rest_cfg.data['static']['dir'],
            debug=True,
            skybase={
                'rest_cfg': rest_cfg
            },
        )

    def parse_options(self):
        # create arg parser and arguments
        parser = argparse.ArgumentParser()

        parser.add_argument(
            '-p', '--port',
            dest='port',
            default=8880,
            action='store')

        parser.add_argument(
            '--config',
            dest='config_dir',
            action='store',
            default=sky_cfg.DEFAULT_CONFIG_DIR,
            help='location of skybase configuration files'
        )

        parser.add_argument(
            '-l',
            '--log-level',
            dest='log_level',
            action='store',
            default='info',
            help='logging level'
        )

        # parse CLI options
        args = parser.parse_args()

        # set restapi attributes from options
        self.port = args.port
        self.log_level = args.log_level


    def run(self):
        # start skybase restapi service
        self.http_server = tornado.httpserver.HTTPServer(self.application)
        self.http_server.listen(self.port)
        enable_pretty_logging()
        tornado.ioloop.IOLoop.instance().start()


end_point_paths['IndexHandler'] = r"/index/?"
class IndexHandler(tornado.web.RequestHandler):
    response = SkyResponse()

    def get(self):
        response = SkyResponse()
        response.code = self.get_status()
        response.status = 'success'
        response.data = {
            'endpoints:': end_point_paths
        }
        response.metadata = {
            'uri': self.request.uri,
        }
        response.message =  'TEST: SERVER INDEX page response'
        self.write(response.response)
        self.finish()


end_point_paths['BootstrapHandler'] = r"/bootstrap-client"
class BootstrapHandler(tornado.web.RequestHandler):
     def get(self):
        self.redirect('/static/bootstrap-skybase-client.sh')


end_point_paths['ApiDescHandler'] = r"/api/([0-9,a-z,A-Z,.\-_]*/?)"
class ApiDescHandler(tornado.web.RequestHandler):
    # TODO: scan and present API endpoints and descriptions
    def get(self, api_version):

        response = SkyResponse()
        response.code = self.get_status()
        response.status = 'success'
        response.data = {
            'endpoints:': end_point_paths
        }
        response.metadata = {
            'api_version': api_version,
            'uri': self.request.uri,
        }
        response.message =  'SkyBase RESTApi Directory'
        self.write(response.response)
        self.finish()

end_point_paths['SkybaseStateDBHandler'] = r"/api/([0-9,a-z,A-Z,.\-_]*)/state/([0-9,a-z,A-Z,\-]*/?)/([0-9,a-z,A-Z,\-]*/?)/([0-9,a-z,A-Z,\-]*/?)"
class SkybaseStateDBHandler(tornado.web.RequestHandler):

    # TODO: authorization of client/role against endpoint + METHOD
    # TODO: routing of endpoint + METHOD to message queue
    # TODO: independent ACL description for API separate from skybase commands

    @authenticated
    def get(self, api_version, planet, service, tag):
        # init RestAPI response container
        response = SkyResponse()

        # construct record id from endpoint path elements
        record_id = os.path.join('/', planet, service, tag)
        tornado_access_log.debug('{0} state db id:{1}'.format(self.request.method, record_id))

        # TODO: need to generalize param handling and passing to celery task; **params possible?
        # handle params
        tornado_access_log.debug('request.query_arguments: {0}'.format(self.request.query_arguments))
        params = dict()

        # expecting 'format' key and no others
        try:
            params['format'] = self.request.query_arguments.get('format')[0]
        except (TypeError, IndexError):
            params['format'] = None

        # execute update state db record task
        kwargs=params
        celery_result = skybase.actions.state.local.read(record_id, **kwargs)

        # prepare json response
        response.data = celery_result
        response.code = self.get_status()
        response.status = 'success'
        response.links = {}
        response.metadata = {
            'restapi': {
                'api_version': api_version,
                'uri': self.request.uri,
                'params': self.request.query_arguments,
                'headers': self.request.headers,
            },
        }

        self.write(response.response)
        self.finish()

    @authenticated
    def put(self, api_version, planet, service, tag):
        # init RestAPI response container
        response = SkyResponse()

        record_id = os.path.join('/', planet, service, tag)
        tornado_access_log.debug('{0} state db id:{1}'.format(self.request.method, record_id))

        record_object = self.request.body

        # execute update state db record task
        kwargs={}
        celery_result = skybase.actions.state.local.update(record_id, record_object, **kwargs)

        # prepare json response
        response.data = celery_result
        response.code = self.get_status()
        response.status = 'success'
        response.links = {}
        response.metadata = {
            'restapi': {
                'api_version': api_version,
                'uri': self.request.uri,
                'params': self.request.query_arguments,
                'headers': self.request.headers,
            },
        }

        self.write(response.response)
        self.finish()

    @authenticated
    def post(self, api_version, planet, service, tag):
        # init RestAPI response container
        response = SkyResponse()

        # deserialize json argument values
        record_args = json.loads(self.request.body)
        tornado_access_log.debug('POST body: {0}'.format(record_args))

        # execute update state db record task
        kwargs=record_args
        celery_result = skybase.actions.state.local.create(**kwargs)

        # prepare json response
        response.data = celery_result
        response.code = self.get_status()
        response.status = 'success'
        response.links = {}
        response.metadata = {
            'restapi': {
                'api_version': api_version,
                'uri': self.request.uri,
                'params': self.request.query_arguments,
                'headers': self.request.headers,
            },
        }

        self.write(response.response)
        self.finish()

end_point_paths['SkybaseTaskHandler'] = r"/api/([0-9,a-z,A-Z,.\-_]*)/task/?([0-9,a-z,A-Z,\-]*/?)"
class SkybaseTaskHandler(tornado.web.RequestHandler):

    # TODO: create message signing utility for use with curl
    # TODO: create skybase group.command for retrieving results using task id
    #@authenticated
    def get(self, api_version, task_id):
        # query backend for task results
        skytask_result = skybase.worker.celery.tasks.app.AsyncResult(task_id)

        response = SkyResponse()
        response.code = self.get_status()
        response.status = 'success'

        response.data = skytask_result.result

        response.metadata = {
            'uri': self.request.uri,
            'api_version': api_version,
            'params': self.request.query_arguments,
            'task_id': skytask_result.task_id,
            'task_status': skytask_result.status,
            'timestamp': skybase.utils.basic_timestamp(),
        }

        self.write(response.response)
        self.finish()

    @authenticated
    def post(self, api_version, task_id):
        '''
        curl -X POST localhost:8888/api/0.1/task/?planet=dev-aws-us-west-1\&group=service\&command=create \
        -d "{'planet': '1'}" \
        -H "SkybSignature: alksdjlfkaj" -H "SkybId: john.doe"
        '''

        access_key = self.request.headers.get(sky_cfg.API_HTTP_HEADER_ACCESS_KEY)
        task_params = self._get_task_params()

        # authorize user against group.command and planet (optional)
        try:
            self._authorize(access_key, **task_params)
        except skybase.exceptions.SkyBaseUserAuthorizationError as e:
            self.set_status(403)
            return self.write(make_error_response(self.get_status(), e))

        # attempt to route task to queue using group, command and planet
        try:
            task_queue = self._get_task_queue(**task_params)
            tornado_access_log.info('task params {0} routed to queue {1}'.format(task_params, task_queue))
        except skybase.exceptions.SkyBaseTaskRoutingError as e:
            self.set_status(400)
            return self.write(make_error_response(self.get_status(), e))

        # prepare skytask runner arguments
        task_name = '.'.join([task_params['group'], task_params['command']])
        task_args = json.loads(self.request.body)['args']

        tornado_access_log.debug('attempt to queue async task ([task, args], queue): ([{0}, {1}], {2})'.format(task_name, task_args, task_queue))
        # execute task in async mode, routing it to derived message queue
        celery_result = skybase.worker.celery.tasks.execute.apply_async(
            args=[task_name, task_args],
            queue=task_queue,
            kwargs={},
        )

        # initialize json response
        response = SkyResponse()

        response.code = self.get_status()
        response.status = 'success'
        response.data = dict()
        response.links = {
            'result': {
                'href': '{0}/{1}'.format(
                    skybase.api.create_api_url(
                        server=self.application.settings['skybase']['rest_cfg'].data['restapi_server_url'],
                        route='task',
                    ),
                    celery_result.task_id
                )
            }
        }
        response.metadata = {
            'restapi': {
                'api_version': api_version,
                'uri': self.request.uri,
                'params': self.request.query_arguments,
                'headers': self.request.headers,
            },
            'client': json.loads(self.request.body)['metadata'],
            'task': {
                'task_name': task_name,
                'queue': task_queue,
                'task_id': str(celery_result.task_id),
                'task_status': str(celery_result.status),
            }
        }

        self.write(response.response)
        self.finish()


    def _authorize(self, access_key, group, command, planet=None):

        is_authorized = skybase.skymap.can_modify_planet(
            access_key=access_key,
            group=group,
            command=command,
            planet=planet)

        msg = 'authentication id {0} for {1}.{2}.{3}: {4}'.format(
            access_key,
            group,
            command,
            planet,
            is_authorized,
        )

        tornado_access_log.debug(msg)

        if not is_authorized:
            raise skybase.exceptions.SkyBaseUserAuthorizationError(msg)

        return is_authorized


    def _get_task_params(self):
        params = dict()
        tornado_access_log.debug('request.query_arguments: {0}'.format(self.request.query_arguments))
        try:
            params['group'] = self.request.query_arguments.get('group')[0]
        except (TypeError, IndexError):
            params['group'] = None

        try:
            params['command'] = self.request.query_arguments.get('command')[0]
        except (TypeError, IndexError):
            params['command'] = None

        # planet parameter is optional
        try:
            params['planet'] = self.request.query_arguments.get('planet')[0]
        except (TypeError, IndexError):
            params['planet'] = ''

        return params

    def _get_task_queue(self, group, command, planet):
        task_queues = skybase.skymap.get_allowed_routes(
            family=group,
            command=command,
            planet=planet,
            routing_map=self.application.settings['skybase']['rest_cfg'].data['queues']
        )
        tornado_access_log.debug('_get_task_queue({0}) == {1}'.format((group, command, planet), task_queues))
        # REST api currently requires one and only only queue for correct routing
        if len(task_queues) == 1:
            return task_queues[0]
        else:
            # TODO: route to error queue or raise Skybase routing error
            raise skybase.exceptions.SkyBaseTaskRoutingError(
                'cannot route task (group, command, planet): {0}'.format((group, command, planet))
            )

import os

from skybase.skytask import SkyTask


def reference_test_add_arguments(parser):
    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )
    parser.add_argument(
        '-t', '--testmessage',
        dest='testmessage',
        action='store',
        default='reference_test_message',
        help='execution mode (default REST api)'
    )


class Test(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):

        SkyTask.__init__(self, all_args, runner_cfg)
        # set the full name of the task 'group.command'
        self.name = 'reference.test'
        self.args = all_args
        self.runner_cfg = runner_cfg

    def execute(self):

        message = self.args['testmessage']

        with open('tmpfile','w') as fw:
            fw.write((message))
        with open('tmpfile', 'r') as fr:
            output = fr.readline()
        if os.path.exists('tmpfile'):
            os.remove('tmpfile')

        self.result.output = output

        # populate attributes for next task
        self.result.next_task_name = 'reference.test'
        self.result.next_args = self.args.copy()
        self.result.next_args['testmessage'] = 'Next -- ' + message

        return self.result

    def preflight_check(self):

        if not self.args['apply']:
            self.preflight_check_result.status = 'FAIL'
            self.preflight_check_result.set_output('for this task you have to use --apply option')

        return self.preflight_check_result

from skybase.skytask import SkyTask


def reference_hello_world_add_arguments(parser):
    parser.add_argument(
        '-m', '--mode',
        dest='exec_mode',
        action='store',
        choices={'local', 'restapi'},
        default='restapi',
        help='execution mode (default REST api)'
    )


class HelloWorld(SkyTask):
    def __init__(self, all_args=None, runner_cfg=None):
        SkyTask.__init__(self, all_args, runner_cfg)
        # set the full name of the task 'group.command'
        self.name = 'reference.hello_world'
        self.args = all_args
        self.runner_cfg = runner_cfg


    def execute(self):
        self.result.output = 'hello world!'

        # TODO: post-processing action using 'next' arguments on artificial trigger, presence of --apply
        if self.args.get('apply'):
            self.result.next_task_name = 'route.ping'
            self.result.next_args.update({
                'count': 1,
                'sleep_interval': .01,
                'apply': True,
            })

        return self.result



    def preflight_check(self):
        return self.preflight_check_result



# Service is the main Unit on which the skybase operates:
# Service consists of stacks:
#   Stack consists of Roles:
#      Role consists of Instances with the same function:
#        Instance is a server ( VM for now, container or bare metal later


class SkyService(object):
    def __init__(self):
        self.name = ''
        self.version = ''
        self.keypair_name = ''
        self.tag_list = []

        self.stack_list = []

    def add_stack(self, stack):

        self.stack_list.append(stack)

    def update_stack(self, stack_name, stack):

        pass



class SkyStack(object):
    def __init__(self):
        self.name = ''
        self.type = ''
        self.stack_jinja_template_name = ''
        self.provison_type = ''   # chef-client | chef-solo | ...
        self.state_status = ''   # 'empty' | 'loaded_from_file' | 'verified'

        self.role_list = []

    def add_role(self, role):

        self.role_list.append(role)


class SkyRole(object):
    def __init__(self):
        self.name = ''
        self.userdata_jinja_template_name = ''
        self.maintenance_type = ''
        self.autoscaling_flag = None   # True | False
        self.autoscaling_min = 1
        self.autoscaling_max = 1
        self.subnet_name = ''
        self.vpc_zone_identifier = ''  # can be 'private' | 'public'
        self.instance_profile['image_name'] = ''
        self.instance_profile['intance_type'] = ''
        self.instance_profile['root_volume_size'] = ''
        self.chef_role_name = ''       # chef role name for the chef-client type
        self.chef_role_runlist = ''    # chef runlist (explicit list of recipes, no roles) for both chef-client and solo

        self.instance_list = []

    def add_instance(self, vm):

        self.instance_list(vm)


class SkyInstance(object):
    def __init__(self):
        self.name = ''
        self.vm_provider = ''   # ec2 | os | docker | ...
        self.ip = ''

    def set_name(self, name):
        self.name = name

    def set_ip(self, ip):
        self.ip = ip







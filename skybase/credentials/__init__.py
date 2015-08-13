

'''
Note: Credentials are associated with the "target operands" e.g. planet
All what we are doing is to put "Something" into "Somewhere"
credentials are needed to do control "Somewhere"
'''

class Credentials(object):
    '''
    Credentials is an object with info to connect to providers
    types: chef | aws | openstack | salt_master
    '''
    def __init__(self):

        self.type = ''
        self.endpoint = ''
        self.config_file_template = ''
        self.access_key = ''
        self.secret_key = ''
        self.private_key_file = ''
        self.public_key_file = ''

        pass

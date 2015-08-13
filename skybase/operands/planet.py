
import yaml
import yaml.parser
import yaml.scanner

from skybase import utils as ut
from skybase import exceptions as sky_exception

# for dict_merge
import types


# Note: after changing schema do not forget to update test data "test-planet"
planetSchema = [
    [['definition'], []],
    [['definition', 'name'], ['str']],
    [['definition', 'universe'], ['str']],
    [['definition', 'provider'], ['str']],
    [['definition', 'orchestration_engine'], ['str']],
    [['definition', 'accountprofile'], ['str']],
    [['definition', 'region'], ['str']],

    [['definition', 'images'],[]],
    [['definition', 'images', 'standard'],[]],
    [['definition', 'images', 'standard', 'id'], ['str']],
    [['definition', 'images', 'standard', 'user'], ['str']],

    [['services'], []],

    [['resource_ids', 'planet_stack_id'],['str']],
    [['resource_ids', 'vpc_id'],['str']],
    [['resource_ids', 'std_security_groups'], []],
    [['resource_ids', 'std_security_groups', 'consul_client'],['str']],

    [['resource_ids', 'subnets'], []],
    [['resource_ids', 'subnets', 'privateA'], []],
    [['resource_ids', 'subnets', 'privateA', 'id'],['str']],
    [['resource_ids', 'subnets', 'privateA', 'az'],['str']],
    [['resource_ids', 'subnets', 'privateA', 'ip'],['str']],
    [['resource_ids', 'subnets', 'privateA', 'type'],['str']],

    [['resource_ids', 'subnets', 'privateB'], []],
    [['resource_ids', 'subnets', 'privateB', 'id'],['str']],
    [['resource_ids', 'subnets', 'privateB', 'az'],['str']],
    [['resource_ids', 'subnets', 'privateB', 'ip'],['str']],
    [['resource_ids', 'subnets', 'privateB', 'type'],['str']],

    [['resource_ids', 'subnets', 'privateC'], []],
    [['resource_ids', 'subnets', 'privateC', 'id'],['str']],
    [['resource_ids', 'subnets', 'privateC', 'az'],['str']],
    [['resource_ids', 'subnets', 'privateC', 'ip'],['str']],
    [['resource_ids', 'subnets', 'privateC', 'type'],['str']]

]


class Planet(object):
    '''
    Actions to perform with Planet operand
    - read from file the complete planet
    - read from file only definition and services
    - generate empty planet
    - write planet to file (if empty planet was generated, then writing it will create template
    - update_info definition | services | resource_ids
    -
    '''

    def __init__(self, planet_data):

        # set the flag that planet is incomplete
        # it will be set to OK only at the end of validation
        self.complete = False

        pd = planet_data

        try:
            validated = self.validate_planet_data_schema(pd)
        except Exception:
            raise sky_exception.SkyBaseConfigurationError('Data Structure does not match Planet Data Schema')

        # Planet has only 3 sections: definition, services and resource_ids
        # we assign those dict here
        self.definition = ut.getKeyFromDict(pd, ['definition'])
        self.services = ut.getKeyFromDict(pd, ['services'])
        self.resource_ids = ut.getKeyFromDict(pd, ['resource_ids'])


        # print 'WHOLEDEF:   ', self.definition

        # final flag
        self.complete = True

    @classmethod
    def planet_from_file(cls, file_name):

        try:
            planet_data = ut.read_yaml_from_file(file_name)

        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
            print 'Invalid Planet YAML.', e
            raise sky_exception.SkyBaseConfigurationError

        try:
            planet = cls(planet_data)

        except Exception as e:
            raise sky_exception.SkyBasePlanetError(e)

        return planet

    @classmethod
    def planet_from_empty_data(cls):

        planet_data = cls.generate_empty_data()

        planet = cls(planet_data)

        return planet


    def validate_planet_data_schema(self, planet_data):
        global planetSchema

        validated = False

        try:
            missing_list = ut.verify_dict_schema(planetSchema, planet_data)
            if not missing_list:
                validated = True
            else:
                print 'MISSING KEYS in PLANET DATA: ', missing_list
        except:
            print 'wrong data in planet dict'
            validated = False

        if not validated:
            raise sky_exception.SkyBaseConfigurationError

    def generate_empty_data(self):
        '''
        Use Planet schema generate an empty data set for the planet
        :return:
        '''
        global planetSchema
        pd ={}
        for l in planetSchema:
            nd = ut.rec_dict_from_list(l[0])
            pd = ut.rec_dict_merge(pd,nd)

        return pd



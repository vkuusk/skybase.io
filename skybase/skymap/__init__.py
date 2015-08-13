import re
from skybase import config as sky_cfg
from skybase.actions.auth.db import find_user_roles

rest_cfg = sky_cfg.SkyConfig.init_from_file('restapi', config_dir=sky_cfg.CONFIG_DIR)

# extract rule group for queue
def get_rule_group(routes, rule_type):
    return (routes or {}).get(rule_type, []) or []

# return True after first positive rule match
def get_rule_matches(rule_group, command):
    for rule in rule_group:
        if re.match(rule, command):
            return True

def get_allowed_routes(family=None, command=None, planet='', routing_map=None):
    #join command components together as target text for regex pattern match
    command = ' '.join([str(family), str(command), str(planet)])
    allowed_routes = []

    for route in routing_map:
        # extract allow/deny rule groups for route
        allow_rule_group = get_rule_group(routing_map[route], 'allow')
        deny_rule_group = get_rule_group(routing_map[route], 'deny')

        # test command against allow/deny rule groups
        allow = get_rule_matches(allow_rule_group, command)
        deny = get_rule_matches(deny_rule_group, command)

        # test allow/deny match results
        if allow and not deny:
            allowed_routes.append(route)

    return allowed_routes

# TODO: renaming required for group.command.planet AND group.command; can_role_execute_command() maybe?
def role_allowed_for_planet(role, family, command, planet_name, routing_map=rest_cfg.data.get('roles')):
    allowed_roles = get_allowed_routes(family, command, planet_name, routing_map)
    return role in allowed_roles

# TODO: renaming required for group.command.planet AND group.command; can_user_execute_command() maybe?
def can_modify_planet(access_key, group, command, planet, routing_map=rest_cfg.data.get('roles')):
    roles = find_user_roles(access_key)
    # test each role for first allowed access to planet
    for role in roles:
        if role_allowed_for_planet(role, group, command, planet, routing_map):
            return True
    return False
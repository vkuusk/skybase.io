from skybase import schemas

schemas.set_indicators()

#Directory schemas layout of the directories
artiball_schema = [
    [[''],['skybase.yaml']],
    # [['app'], []],
    [['app_config'], ['main_app_config.yaml']],
    [['installation'], []],
    [['installation', 'chef', 'cookbooks'], []],
    [['installation', 'chef', 'databags'], []],
    [['installation', 'chef', 'encrypted_databags'], []],
    [['deployment'], []],
    [['deployment'], ['main_deployment.yaml']],
]

# TODO: move/derive these from artiball schema module
ARTIBALL_SCHEMA_ARGS = {
    'code_dir': 'app',

    'config_dir': 'app_config',
    'config_file': 'main_app_config.yaml',

    'deploy_dir': 'deployment',
    'deploy_file': 'main_deployment.yaml',

    'cookbooks_dir': 'installation/chef/cookbooks',
    'cookbooks_order_file': 'installation/chef/cookbook-order.yaml',
    'encrypted_data_bag_secret': 'chef/COMMON/encrypted_data_bag_secret',
    'databags_dir': 'installation/chef/databags',
    'enc_databags_dir': 'installation/chef/encrypted_databags',

    'manifest_file': 'manifest.yaml',
}

#File Schema sets

#skybase.yaml schema set
skybase_yaml_schema = [
     '''#Configuration file to inform SkyBase client about your application layout.''',
    [['packing'], []],
    [['packing', 'application'], []],
    [['packing', 'application', 'source_location'], [schemas.STR_TYPE_OPTIONAL_INDICATOR]],
    [['packing', 'installations'], [schemas.LIST_TYPE]],
]

skybase_installations_yaml_schema = [
    [['chef', 'repository_url'], [schemas.STR_TYPE_OPTIONAL_INDICATOR]],
    [['chef', 'repository_branch'], [schemas.STR_TYPE_OPTIONAL_INDICATOR]],
    [['chef', 'databags'], [schemas.LIST_TYPE_INDICATOR]],
    [['chef', 'encrypted_databags'], [schemas.LIST_TYPE_INDICATOR]],
    [['chef', 'cookbooks', 'dependencies_from_berkshelf'], [schemas.BOOL_TYPE_INDICATOR]],
]


#main_deployment.yaml schema set
main_deployment_yaml_schema = [
    '''#SkyBase Template (SBT) to describe resources for the service and dependencies.''',

    [['definition'], []],
    [['definition', 'service_name'], [schemas.STR_TYPE_INDICATOR]],
    [['definition', 'version'], [schemas.STR_TYPE_INDICATOR]],
    [['definition', 'keyname'], [schemas.STR_TYPE_INDICATOR]],
    [['definition', 'chef_type'], [schemas.STR_TYPE_INDICATOR]],
    [['definition', 'tags'], []],
    [['definition', 'tags', 'TeamID'], [schemas.STR_TYPE_INDICATOR]],
    [['definition', 'tags', 'ServiceID'], [schemas.STR_TYPE_INDICATOR]],
    [['definition', 'tags', 'Email'], [schemas.STR_TYPE_INDICATOR]],
    [['stacks'], [schemas.LIST_TYPE]],
]

main_deployment_stacks_yaml_schema = [
    [['name'], [schemas.STR_TYPE_INDICATOR]],
    [['type'], [schemas.STR_TYPE_INDICATOR]],
    [['cloud_template_name'], [schemas.STR_TYPE_INDICATOR]],
    [['roles'], [schemas.LIST_TYPE]],
]

main_deployment_stacks_roles_yaml_schema = [
    [['name'], [schemas.STR_TYPE_INDICATOR]],
    [['userdata_template_name'], [schemas.STR_TYPE_INDICATOR]],
    [['type'], [schemas.STR_TYPE_INDICATOR]],
    [['ami'], [schemas.STR_TYPE_INDICATOR]],
    [['subnet'], [schemas.STR_TYPE_INDICATOR]],
    [['instance_type'], [schemas.STR_TYPE_INDICATOR]],
    [['root_volume_size'], [schemas.INT_TYPE_INDICATOR]],
    [['chef_role_runlist'], [schemas.LIST_TYPE_INDICATOR]],
    [['autoscaling'], [schemas.INT_TYPE_INDICATOR]],
    [['vpc_zone_identifier'], [schemas.STR_TYPE_INDICATOR]],
    [['initial_capacity'], [schemas.INT_TYPE_INDICATOR]],
    [['max_capacity'], [schemas.INT_TYPE_INDICATOR]],
]


#main_app_config.yaml schema set
main_app_config_yaml_schema = [
    '''#SkyBase Template (SBT) to configure your application.''',
    [['common', schemas.DICT_KEY_TYPE_INDICATOR], [schemas.DICT_VALUE_TYPE_INDICATOR]],
    [['stacks'], [schemas.LIST_TYPE]],
]

main_app_config_stacks_yaml_schema = [
    [['name'], [schemas.STR_TYPE_INDICATOR]],
    [['roles'], [schemas.LIST_TYPE]],
]

main_app_config_stacks_roles_yaml_schema = [
    [['name'], [schemas.STR_TYPE_INDICATOR]],
    [['universes', 'dev', schemas.DICT_KEY_TYPE_INDICATOR], [schemas.DICT_VALUE_TYPE_INDICATOR]],
    [['universes', 'qa', schemas.DICT_KEY_TYPE_INDICATOR], [schemas.DICT_VALUE_TYPE_INDICATOR]],
    [['universes', 'prod', schemas.DICT_KEY_TYPE_INDICATOR], [schemas.DICT_VALUE_TYPE_INDICATOR]]
]

#TODO: discuss flattening manifest, removing metadata; any changes here must be couple with changes to Arbiball().manifest property
#manifest.yaml schema
manifest_yaml_schema = [
    [['metadata', 'app_name'], [schemas.STR_TYPE_INDICATOR]],
    [['metadata', 'app_version'], [schemas.STR_TYPE_INDICATOR]],
    [['metadata', 'build_id'], [schemas.STR_TYPE_INDICATOR]],
    [['chef_cookbook_source'], [schemas.STR_TYPE_INDICATOR]]
]
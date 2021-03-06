import os
from skybase import config as sky_cfg
from skybase.utils.schema import read_yaml_from_file
from skybase.api.salt import SkySaltAPI
import skybase.skytask.service.update

def get_creds_file(config_dir=None):
    if not config_dir:
        runner_cfg = sky_cfg.SkyConfig.init_from_file('runner', config_dir=sky_cfg.CONFIG_DIR)
        config_dir = runner_cfg.data['runner_credentials_dir']
    config_file = 'salt/credentials.yaml'
    return os.path.join(config_dir, config_file)

def get_saltapi_authtoken(runner_cfg, planet_name=None):
    # acquire salt api connection
    api_creds = read_yaml_from_file(get_creds_file())
    api = SkySaltAPI(
        username=api_creds['username'],
        password=api_creds['password'],
        runner_cfg=runner_cfg,
        planet_name=planet_name,
    )
    api.authorize()
    return api.authtoken

def test_ping_by_grain(grain, runner_cfg=None, authtoken=None, planet_name=None):
    if authtoken is None:
        authtoken = get_saltapi_authtoken(runner_cfg)

    saltapi = SkySaltAPI(
        planet_name=planet_name,
        authtoken=authtoken
    )
    _, result = saltapi.test_ping(tgt=grain, **{'expr_form': 'grain'})

    return result['return']

def get_host_by_grain(grain, runner_cfg=None, authtoken=None, planet_name=None):
    if authtoken is None:
        authtoken = get_saltapi_authtoken(runner_cfg)

    saltapi = SkySaltAPI(
        planet_name=planet_name,
        authtoken=authtoken
    )
    _, result = saltapi.grains_item(tgt=grain, expr_form='grain', arg=['host',])

    return result['return']

def update_service(stacks, service, runtime, update_plan, runner_cfg=None, authtoken=None,):

    # skybase provided plans
    skybase_update_plans = skybase.skytask.service.update.skybase_update_plans

    result = dict()

    if runtime.apply and update_plan in skybase_update_plans:
        if authtoken is None:
            authtoken = get_saltapi_authtoken(runner_cfg, planet_name=service.planet)

        saltapi = SkySaltAPI(
            planet_name=service.planet,
            authtoken=authtoken,
        )

        # update all roles in designated stacks
        for stack in stacks:
            # get salt grain identifying stacks in service
            stack_grain = service.stacks.stacks[stack].salt_grain_skybase_id

            # apply fixed/constant service update method to rerun cfn-init and chef
            _, upd_result = saltapi.update_service(
                tgt=stack_grain,
                action=skybase_update_plans.get(update_plan))

            result[stack] = {
                'saltapi': upd_result['return'],
                'stacks': stacks,
                'update_plan': update_plan,
            }

    else:
        # provide simple list of stacks designated for update
        result = {
            'stacks': stacks,
            'update_plan': update_plan,
        }

    return result
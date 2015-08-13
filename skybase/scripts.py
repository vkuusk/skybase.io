#!/usr/bin/env python

def sky_cli():
    from skybase.cli import SkyCmd as cli
    command = cli.SkyCmd()
    command.run()


def sky_restapi():
    from skybase.restapi import SkyRestAPI as restapi
    r_process = restapi()
    r_process.run()
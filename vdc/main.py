import logging
from importlib.metadata import version

import click

from vdc.open import setup_env

vdc_version = version("vdl-cli")


@click.group(name="cli")
@click.version_option(vdc_version, "--version", "-v", help="Show version and exit")
def cli(): ...


@cli.command()
@click.option("--verbose", is_flag=True, help="Print verbose output")
def open(verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    setup_env()


# @cli.command()
# @click.argument("db", nargs=1, required=True)
# @click.argument("to", nargs=1, required=True)
# @click.option("--usage", "-u", multiple=True, help="Grant usage to role")
# def clone(db, to, usage):
#    from vdc.clone import create_db_clone
#
#    create_db_clone(src=db, dst=to, usage=usage)


@cli.command()
@click.argument("table", nargs=1, required=True)
@click.argument("primary_key", nargs=1, required=True)
@click.option("--compare-to", "-c", help="Database you want to compare against")
def diff(table, primary_key, compare_to):
    from vdc.diff import table_diff

    table_diff(table, primary_key, compare_to)

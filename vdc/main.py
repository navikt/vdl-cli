import logging
import os
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
@click.option(
    "--compare-to-db",
    "-d",
    help="Database you want to compare against. Default is dev_<user>_<db> where <user> is your username and <db> is the database of the provided table",
)
@click.option(
    "--compare-to-schema",
    "-s",
    help="Schema you want to compare against Default is same as provided table",
)
@click.option(
    "--compare-to-table",
    "-t",
    help="Table you want to compare against. Default is same as provided table",
)
@click.option("--column", "-c", multiple=True, help="Only compare column")
@click.option("--ignore-column", "-i", multiple=True, help="Ignore column")
def diff(
    table,
    primary_key,
    compare_to_db,
    compare_to_schema,
    compare_to_table,
    column,
    ignore_column,
):
    from vdc.diff import table_diff

    full_table_name = table
    db, schema, table = table.split(".")
    compare_to_db = compare_to_db or f"dev_{os.environ['USER']}_{db}"
    compare_to_schema = compare_to_schema or schema
    compare_to_table = compare_to_table or table
    compare_to = f"{compare_to_db}.{compare_to_schema}.{compare_to_table}"

    table_diff(
        table=full_table_name,
        primary_key=primary_key,
        compare_to=compare_to,
        columns=column,
        ignore_columns=ignore_column,
    )

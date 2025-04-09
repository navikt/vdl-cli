import logging
import os
from importlib.metadata import version

import click

from vdc.open import setup_env
from vdc.utils import set_config

vdc_version = version("vdl-cli")

config = {
    "snowflake": {
        "account": os.getenv("SNOWFLAKE_ACCOUNT", "wx23413.europe-west4.gcp"),
        "user": os.getenv("SNOWFLAKE_USER") or os.getenv("DBT_USR"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "dev__xs"),
        "authenticator": os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"),
        "role": os.getenv("SNOWFLAKE_ROLE", "sysadmin"),
    }
}

set_config(config)


@click.group(name="cli")
@click.version_option(vdc_version, "--version", "-v", help="Show version and exit")
def cli(): ...


@cli.command()
@click.option("--verbose", is_flag=True, help="Print verbose output")
def open(verbose):
    """Setup and open the environment for the current user"""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    setup_env()


@cli.command()
@click.argument("db", nargs=1, required=True)
@click.argument("to", nargs=1, required=True)
@click.option("--usage", "-u", multiple=True, help="Grant usage to role")
def clone(db, to, usage):
    """Clone a database"""
    from vdc.clone import create_db_clone

    create_db_clone(src=db, dst=to, usage=usage)


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
    """Compare two tables in Snowflake"""
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


@cli.group(name="waste")
def waste():
    """Commands for marking db objects as waste or removing marked objects"""
    pass


@waste.command()
@click.option(
    "--dbt-project-dir", "-d", default="dbt", help="Path to dbt project directory"
)
@click.option(
    "--dbt-profile-dir", "-p", default="dbt", help="Path to dbt profile directory"
)
@click.option("--dbt-target", "-t", default="prod", help="dbt profile target")
# @click.option("--ignore-table", "-i", multiple=True, help="Ignore table from search")
# @click.option("--schema", "-s", multiple=True, help="Schema to search in")
def disposal(
    dbt_project_dir,
    dbt_profile_dir,
    dbt_target,
    #    ignore_table,
    #    schema,
):
    """Mark db objects for removal"""
    from vdc.waste import mark_objects_for_removal

    mark_objects_for_removal(
        dbt_project_dir=dbt_project_dir,
        dbt_profile_dir=dbt_profile_dir,
        dbt_target=dbt_target,
        #        ignore_table=ignore_table,
        #        schema=schema,
    )


@waste.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry run and print potential removals",
)
def incineration(dry_run):
    """Drop database objects marked for removal"""
    from vdc.waste import remove_marked_objects

    remove_marked_objects(dry_run=dry_run)

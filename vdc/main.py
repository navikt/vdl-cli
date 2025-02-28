import subprocess
import sys
import click
from importlib.metadata import version


vdc_version = version("vdc")


@click.group(name="cli", invoke_without_command=True)
@click.version_option(vdc_version, "--version", "-v", help="Show version and exit")
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        open()


@cli.command()
def open():
    import os.path
    if os.path.isfile("vdl_project.yaml"):
        ...
    if os.path.isfile("setup_env.sh"):
        subprocess.run(["./setup_env.sh"])
        return
    print("Could not find vdl_project.yml or setup_env.sh")
    sys.exit(1)

#@cli.command()
#@click.argument("db", nargs=1, required=True)
#@click.argument("to", nargs=1, required=True)
#@click.option("--usage", "-u", multiple=True, help="Grant usage to role")
#def clone(db, to, usage):
#    from vdc.clone import create_db_clone
#
#    create_db_clone(src=db, dst=to, usage=usage)


@cli.command()
@click.argument("table", nargs=1, required=True)
@click.argument("primary_key", nargs=1, required=True)
def diff(table, primary_key):
    from vdc.diff import table_diff

    table_diff(table, primary_key)

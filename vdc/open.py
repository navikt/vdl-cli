import logging
import os
import subprocess
from pathlib import Path
from shutil import which

import yaml
from alive_progress import alive_bar
from click import clear, echo
from jinja2 import Environment

from vdc.utils import _spinner

LOGGER = logging.getLogger(__name__)


def _env_override(value, default=None):
    return os.getenv(value, default)


def _render_template(template):
    env = Environment()
    ddl_template = env.from_string(template)
    return ddl_template.render(env_var=_env_override)


def _selector(options):
    while True:
        echo("Available targets:")
        options = list(options)
        for i, option in enumerate(options):
            echo(f"{i+1}) {option}")
        selected = input("Select target: ")
        if selected.isdigit() and 0 < int(selected) <= len(options):
            return options[int(selected) - 1]
        echo("Invalid selection")
        echo("")


def _validate_target(targets, default_targets):
    default_targets = set(default_targets)
    if not default_targets.issubset(targets):
        return ValueError(
            "dbt target outputs for dev and prod should exist in dbt profiles.yml"
        )
    databases = [targets[target]["database"] for target in default_targets]
    if len(set(databases)) != len(databases):
        return ValueError(
            f"{' and '.join(default_targets)} should have different databases in dbt profiles.yml"
        )
    if targets["prod"]["database"] == targets["dev"]["database"]:
        return ValueError(
            "dev and prod should have different databases in dbt profiles.yml"
        )
    existing_target = os.getenv("DBT_TARGET")
    if existing_target and existing_target not in default_targets:
        return ValueError(
            f"DBT_TARGET={existing_target} is not a valid target. Use one of {', '.join(default_targets)}"
        )

    return None


def _print_banner():
    banner_dir = os.path.dirname(__file__)
    banner_file = Path(f"{banner_dir}/banner.txt")
    banner = banner_file.read_text()
    if banner_file.exists():
        echo(f"\n{banner}\n")


def _get_dbt_targets(project_file, profile_file):

    project = yaml.safe_load(project_file.read_text())

    profile_name = project["profile"]
    profiles = yaml.safe_load(_render_template(profile_file.read_text()))
    project_profile = profiles[profile_name]

    targets = project_profile["outputs"]

    return targets


def _validate_dbt_targets(targets, default_targets):
    error = _validate_target(targets=targets, default_targets=default_targets)
    if error:
        LOGGER.error(error)
        exit(1)
    LOGGER.info("dbt project configuration is ok")


def _validate_file(file):
    if not file.exists():
        LOGGER.error(f"Could not find {file}")
        exit(1)
    LOGGER.info(f"Found file: {file}")


def _validate_dbt_user(user):
    if user == "None":
        LOGGER.error(
            "\ndbt target user is not defined in dbt profiles.yml. Please define a user for the target\n"
        )
        exit(1)


def _validate_program(program):
    if which(program) is None:
        LOGGER.error(f"\n{program} is not installed. Please install it.\n")
        exit(1)
    LOGGER.info(f"Found program: {program}")


def _install_environment():
    with _spinner("Installing environment"):
        make_install = subprocess.run(["make"], capture_output=True)
    if (
        make_install.returncode != 0
        or make_install.stdout.decode(encoding="utf-8")
        == "make: Nothing to be done for `install'.\n"
    ):
        LOGGER.error(
            "Failed to install environment. Please check if 'make install' works."
        )
        exit(1)
    LOGGER.info("Environment installed")


def _replace_dev_database(prod_target_database, selected_database, selected_role):
    assert (
        prod_target_database != selected_database
    )  # should not happen because of validate_target

    snowbird_command = [
        ".venv/bin/snowbird",
        "clone",
        prod_target_database,
        selected_database,
        "--usage",
        selected_role,
    ]
    with _spinner("Replacing database"):
        replace_database_output = subprocess.run(snowbird_command, capture_output=True)

    if replace_database_output.returncode != 0:
        print("Failed to replace database")
        exit(1)
    print("Database replaced")
    print("")


def _setup_snowbird(config=None):
    config = config or {
        "user": os.environ["DBT_USR"],
        "account": "wx23413.europe-west4.gcp",
        "warehouse": "dev__xs",
        "database": "test_db",
        "role": "securityadmin",
        "authenticator": "externalbrowser",
    }

    selected_user = config["user"]
    os.environ["PERMISSION_BOT_USER"] = selected_user
    selected_account = config["account"]
    os.environ["PERMISSION_BOT_ACCOUNT"] = selected_account
    selected_warehouse = config["warehouse"]
    os.environ["PERMISSION_BOT_WAREHOUSE"] = selected_warehouse
    selected_database = config["database"]
    os.environ["PERMISSION_BOT_DATABASE"] = selected_database
    selected_role = config["role"]
    os.environ["PERMISSION_BOT_ROLE"] = selected_role
    selected_authenticator = config["authenticator"]
    os.environ["PERMISSION_BOT_AUTHENTICATOR"] = selected_authenticator

    return config


def setup_env():
    clear()
    _print_banner()
    LOGGER.info("Validating project configuration\n")

    _validate_program("code")

    taskfile = Path("taskfile.dist.yaml")
    if not taskfile.exists():
        LOGGER.warning("taskfile.dist.yaml not found. Using make instead of task")
        _validate_program("make")
        makefile = Path("Makefile")
        _validate_file(makefile)

    LOGGER.info("Setting up environment")
    pip_file = Path(".venv/bin/pip")
    if not pip_file.exists():
        echo("No python environment found.")
        _install_environment()
    requirements_lock = Path("requirements-lock.txt")
    freeze_output = subprocess.run(
        [".venv/bin/pip", "freeze"],
        capture_output=True,
    )
    environment_content = freeze_output.stdout.decode(encoding="utf-8")
    if not requirements_lock.exists():
        LOGGER.warning("requirements-lock.txt not found. Skipping comparison")
    if requirements_lock.exists():
        LOGGER.info("Found requirements-lock.txt")
        LOGGER.info("Comparing environment with requirements-lock.txt")

        requirements_lock_content = requirements_lock.read_text()
        requirements_lock_packages = set(requirements_lock_content.splitlines())
        envrionment_packages = set(environment_content.splitlines())
        if not requirements_lock_packages.issubset(envrionment_packages):
            echo("Environment does not match requirements-lock.txt.")
            _install_environment()
            freeze_output = subprocess.run(
                [".venv/bin/pip", "freeze"],
                capture_output=True,
            )
            environment_content = freeze_output.stdout.decode(encoding="utf-8")
        else:
            LOGGER.info("Environment matches requirements-lock.txt")
        print("")

    snowbird_is_installed = "snowbird" in environment_content
    if not snowbird_is_installed:
        LOGGER.warning("snowbird is not installed in environment. Skipping setup")
    if snowbird_is_installed:
        LOGGER.info("Found snowbird in environment")
        LOGGER.info("Setting up snowbird")
        snowbird_config = _setup_snowbird()
        LOGGER.info("snobird config:")
        LOGGER.info(snowbird_config)

    dbt_is_installed = "dbt-core" and "dbt-snowflake" in environment_content
    if not dbt_is_installed:
        LOGGER.warning(
            "dbt-core or dbt-snowflake is not installed in environment. Skipping setup"
        )
        continue_witouth_dbt = (
            input("Are you sure you want to continue? Y/n: ").lower() != "n"
        )
        if not continue_witouth_dbt:
            exit(0)

    if dbt_is_installed:
        LOGGER.info("Found dbt in environment")
        dbt_project_file = Path("dbt/dbt_project.yml")
        _validate_file(dbt_project_file)
        profile_file = Path("dbt/profiles.yml")
        _validate_file(profile_file)

        default_dbt_targets = ["dev", "prod"]
        dbt_targets = _get_dbt_targets(
            project_file=dbt_project_file,
            profile_file=profile_file,
        )
        _validate_dbt_targets(targets=dbt_targets, default_targets=default_dbt_targets)

        echo("Select dbt target output")
        selected_target = _selector(default_dbt_targets)
        selected_dbt_target = dbt_targets[selected_target]
        selected_database = selected_dbt_target["database"]
        selected_role = selected_dbt_target["role"]
        selected_user = selected_dbt_target["user"]

        _validate_dbt_user(selected_user)

        os.environ["DBT_TARGET"] = selected_target

        LOGGER.info(f"Selected target username: {selected_user}")
        LOGGER.info(f"Selected target database: {selected_database}")
        LOGGER.info(f"Selected target role: {selected_role}")
        LOGGER.info("\ndbt setup is done\n")

        if dbt_is_installed and snowbird_is_installed and selected_target != "prod":
            prod_target_database = dbt_targets["prod"]["database"]
            replace_selected_database = (
                input(
                    f"\nReplace database '{selected_database}'\nwith a clone of database '{prod_target_database}'\nand give usage to role '{selected_role}'? y/N: "
                ).lower()
                == "y"
            )
            if replace_selected_database:
                echo(
                    f"Replacing {selected_database} with a clone of {prod_target_database}"
                )
                _replace_dev_database(
                    prod_target_database=prod_target_database,
                    selected_database=selected_database,
                    selected_role=selected_role,
                )

    echo("Launching vscode")
    subprocess.run("source .venv/bin/activate && code .", shell=True)

import logging
import os
import subprocess
from pathlib import Path

import yaml
from click import clear, echo
from jinja2 import Environment

from vdc.clone import create_db_clone
from vdc.utils import _spinner, _validate_program

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
    try:
        databases = [targets[target]["database"] for target in default_targets]
    except TypeError as e:
        LOGGER.error(f"Error loading dbt profile file. No target database found. {e}")
        exit(1)
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

    try:
        roles = [targets[target]["role"] for target in default_targets]
    except KeyError as e:
        LOGGER.error(f"Error loading dbt profile file. No target role found. {e}")
        exit(1)

    try:
        users = [targets[target]["user"] for target in default_targets]
    except KeyError as e:
        LOGGER.error(f"Error loading dbt profile file. No target user found. {e}")
        exit(1)

    return None


def _print_banner():
    banner_dir = os.path.dirname(__file__)
    banner_file = Path(f"{banner_dir}/banner.txt")
    banner = banner_file.read_text()
    if banner_file.exists():
        echo(f"\n{banner}\n")


def _get_dbt_targets(project_file, profile_file):

    try:
        project = yaml.safe_load(project_file.read_text())
        profile_name = project["profile"]
        profiles = yaml.safe_load(_render_template(profile_file.read_text()))
        project_profile = profiles[profile_name]
    except TypeError as e:
        LOGGER.error(
            f"Error loading dbt project file or profile file. No profile found. {e}"
        )
        exit(1)
    except KeyError as e:
        LOGGER.error(f"Error loading profile file. Profile not found. {e}")
        exit(1)
    except Exception as e:
        LOGGER.error(f"Error loading dbt project file or profile file. {e}")
        exit(1)

    try:
        targets = project_profile["outputs"]
    except TypeError as e:
        LOGGER.error(f"Error loading profile file. Outputs not found. {e}")
        exit(1)
    except Exception as e:
        LOGGER.error(f"Error loading dbt profile file. {e}")
        exit(1)

    if targets is None:
        LOGGER.error("No dbt target outputs found in dbt profiles.yml")
        exit(1)

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


def _validate_dbt_database(database):
    if database is None:
        LOGGER.error(
            "\ndbt target database is not defined in dbt profiles.yml. Please define a database for the target\n"
        )
        exit(1)


def _validate_dbt_role(role):
    if role is None:
        LOGGER.error(
            "\ndbt target role is not defined in dbt profiles.yml. Please define a role for the target\n"
        )
        exit(1)


def _validate_dbt_user(user):
    if user is None:
        LOGGER.error(
            "\ndbt target user is not defined in dbt profiles.yml. Please define a user for the target\n"
        )
        exit(1)


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

    create_db_clone(
        src=prod_target_database, dst=selected_database, usage=(selected_role,)
    )
    print("Database replaced")
    print("")


def setup_env():
    clear()
    _print_banner()
    LOGGER.info("Validating project configuration\n")

    makefile = Path("Makefile")
    _validate_file(makefile)

    _validate_program("code")
    _validate_program("make")

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

    dbt_is_installed = "dbt-core" and "dbt-snowflake" in environment_content
    if not dbt_is_installed:
        LOGGER.warning(
            "dbt-core or dbt-snowflake is not installed in environment. Skipping setup"
        )
        continue_without_dbt = (
            input("Are you sure you want to continue? Y/n: ").lower() != "n"
        )
        if not continue_without_dbt:
            exit(0)

    if dbt_is_installed:
        LOGGER.info("Found dbt in environment")
        dbt_project_file = Path("dbt/dbt_project.yml")
        profile_file = Path("dbt/profiles.yml")
        dbt_files_exist = dbt_project_file.exists() and profile_file.exists()

        if not dbt_files_exist:
            LOGGER.warning(
                "dbt-core and dbt-snowflake are installed in environment, but could not find dbt_project.yml and/or profiles.yml.\nSkipping setup"
            )
            continue_without_dbt = (
                input("Are you sure you want to continue? Y/n: ").lower() != "n"
            )
            if not continue_without_dbt:
                exit(0)

        if dbt_files_exist:
            default_dbt_targets = ["dev", "prod"]
            dbt_targets = _get_dbt_targets(
                project_file=dbt_project_file,
                profile_file=profile_file,
            )
            _validate_dbt_targets(
                targets=dbt_targets, default_targets=default_dbt_targets
            )

            echo("Select dbt target output")
            selected_target = _selector(default_dbt_targets)
            selected_dbt_target = dbt_targets[selected_target]
            selected_database = selected_dbt_target["database"]
            selected_role = selected_dbt_target["role"]
            selected_user = selected_dbt_target["user"]

            _validate_dbt_database(selected_database)
            _validate_dbt_role(selected_role)
            _validate_dbt_user(selected_user)

            os.environ["DBT_TARGET"] = selected_target

            LOGGER.info(f"Selected target username: {selected_user}")
            LOGGER.info(f"Selected target database: {selected_database}")
            LOGGER.info(f"Selected target role: {selected_role}")
            LOGGER.info("\ndbt setup is done\n")

            if selected_target != "prod":
                prod_target_database = dbt_targets["prod"]["database"]
                _validate_dbt_database(prod_target_database)
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

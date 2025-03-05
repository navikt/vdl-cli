import os
import subprocess
from pathlib import Path
from shutil import which

import yaml
from jinja2 import Environment


def _env_override(value, default=None):
    return os.getenv(value, default)


def _render_template(template):
    env = Environment()
    ddl_template = env.from_string(template)
    return ddl_template.render(env_var=_env_override)


def _selector(options):
    while True:
        print("Available targets:")
        options = list(options)
        for i, option in enumerate(options):
            print(f"{i+1}) {option}")
        selected = input("Select target: ")
        if selected.isdigit() and 0 < int(selected) <= len(options):
            return options[int(selected) - 1]
        print("Invalid selection")
        print("")


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
    if banner_file.exists():
        print("")
        print(banner_file.read_text())
        print("")


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
        print(error)
        exit(1)


def _validate_file(file):
    if not file.exists():
        print(f"Could not find {file}")
        exit(1)
    print(f"Found file: {file}")


def _validate_dbt_user(user):
    if user == "None":
        print("")
        print(
            "dbt target user is not defined in dbt profiles.yml. Please define a user for the target"
        )
        print("")
        exit(1)


def _validate_program(program):
    if which(program) is None:
        print(f"\n{program} is not installed. Please install it.\n")
        exit(1)
    print(f"Found program: {program}")


def _install_environment():
    make_install = subprocess.run(["make"], capture_output=True)
    if (
        make_install.returncode != 0
        or make_install.stdout.decode(encoding="utf-8")
        == "make: Nothing to be done for `install'.\n"
    ):
        print("Failed to install environment. Please check if 'make install' works.")
        exit(1)


def _setup_snowbird(selected_dbt_target):
    selected_user = selected_dbt_target["user"]
    print(f"Selected user: {selected_user}")
    os.environ["PERMISSION_BOT_USER"] = selected_user

    selected_account = selected_dbt_target["account"]
    print(f"Selected account: {selected_account}")
    os.environ["PERMISSION_BOT_ACCOUNT"] = selected_account

    selected_warehouse = selected_dbt_target["warehouse"]
    print(f"Selected warehouse: {selected_warehouse}")
    os.environ["PERMISSION_BOT_WAREHOUSE"] = selected_warehouse

    selected_database = selected_dbt_target["database"]
    print(f"Selected database: {selected_database}")
    os.environ["PERMISSION_BOT_DATABASE"] = selected_database

    selected_role = "securityadmin"
    print(f"Selected role: {selected_role}")
    os.environ["PERMISSION_BOT_ROLE"] = selected_role

    selected_authenticator = selected_dbt_target["authenticator"]
    print(f"Selected authenticator: {selected_authenticator}")
    os.environ["PERMISSION_BOT_AUTHENTICATOR"] = selected_authenticator
    print("")


def setup_env():
    _print_banner()
    print("Validating project configuration")
    print("")

    makefile = Path("Makefile")
    _validate_file(makefile)
    requirements = Path("requirements.txt")
    _validate_file(requirements)
    dbt_project_file = Path("dbt/dbt_project.yml")
    _validate_file(dbt_project_file)
    profile_file = Path("dbt/profiles.yml")
    _validate_file(profile_file)
    print("")

    _validate_program("code")
    _validate_program("make")
    print("")

    print("Setting up environment")
    pip_file = Path(".venv/bin/pip")
    if not pip_file.exists():
        print("No python environment found. Installing environment")
        _install_environment()
    requirements_lock = Path("requirements-lock.txt")
    freeze_output = subprocess.run(
        [".venv/bin/pip", "freeze"],
        capture_output=True,
    )
    environment_content = freeze_output.stdout.decode(encoding="utf-8")

    if requirements_lock.exists():
        print("Found requirements-lock.txt")
        print("Comparing environment with requirements-lock.txt")

        requirements_lock_content = requirements_lock.read_text()

        if environment_content != requirements_lock_content:
            print(
                "Environment does not match requirements-lock.txt. Reinstalling environment"
            )
            _install_environment()
        else:
            print("Environment matches requirements-lock.txt")
        print("")

    if environment_content.find("dbt-core") == -1:
        print(
            "dbt-core is not installed in environment. Please add dbt to requirements.txt and update environment"
        )
        exit(1)
    if environment_content.find("dbt-snowflake") == -1:
        print(
            "dbt-snowflake is not installed in environment. Please add dbt-snowflake to requirements.txt and update environment"
        )
        exit(1)

    print("Found dbt in environment")
    print("Setting up dbt")
    default_dbt_targets = ["dev", "prod"]
    dbt_targets = _get_dbt_targets(
        project_file=dbt_project_file,
        profile_file=profile_file,
    )
    _validate_dbt_targets(targets=dbt_targets, default_targets=default_dbt_targets)
    print("dbt project configuration is ok")
    print("")

    print("Select dbt target output")
    selected_target = _selector(default_dbt_targets)
    selected_dbt_target = dbt_targets[selected_target]
    selected_database = selected_dbt_target["database"]
    selected_role = selected_dbt_target["role"]
    selected_user = selected_dbt_target["user"]

    _validate_dbt_user(selected_user)

    os.environ["DBT_TARGET"] = selected_target

    print(f"Selected target username: {selected_user}")
    print(f"Selected target database: {selected_database}")
    print(f"Selected target role: {selected_role}")
    print("")
    print("dbt setup is done")
    print("")

    if "snowbird" in requirements.read_text():
        print("Found snowbird in environment")
        print("Setting up snowbird")
        _setup_snowbird(selected_dbt_target=selected_dbt_target)
        print("snowbird setup is done")
        print("")
        if selected_target != "prod":
            prod_target_database = dbt_targets["prod"]["database"]
            assert (
                prod_target_database != selected_database
            )  # should not happen because of validate_target
            replace_selected_database = (
                input(
                    f"Do you want to replace database '{selected_database}' with a clone of database '{prod_target_database}' and give usage to role '{selected_role}'? y/N: "
                ).lower()
                == "y"
            )
            if replace_selected_database:
                print(
                    f"Replacing {selected_database} with a clone of {prod_target_database}"
                )
                snowbird_command = [
                    ".venv/bin/snowbird",
                    "clone",
                    prod_target_database,
                    selected_database,
                    "--usage",
                    selected_role,
                ]
                replace_database_output = subprocess.run(snowbird_command)

                if replace_database_output.returncode != 0:
                    print("Failed to replace database")
                    exit(1)
                print("Database replaced")
                print("")

    print("Launching vscode")
    subprocess.run("source .venv/bin/activate && code .", shell=True)

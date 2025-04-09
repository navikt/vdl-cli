import datetime
import json
import os
import subprocess
from pathlib import Path

import questionary
import snowflake.connector
from questionary import Choice
from snowflake.connector import DictCursor

from vdc.utils import _validate_program


def _snow_connection():
    config_sso = {
        "user": os.environ["DBT_USR"],
        "account": "wx23413.europe-west4.gcp",
        "role": "sysadmin",
        "warehouse": "dev__xs",
        "authenticator": "externalbrowser",
    }

    return snowflake.connector.connect(**config_sso).cursor(DictCursor)


def _create_dbt_manifest(
    dbt_project_dir: str = "dbt", dbt_profile_dir: str = "dbt", dbt_target: str = "prod"
):
    run_result = subprocess.run(
        [
            "dbt",
            "compile",
            "--target",
            dbt_target,
            "--profiles-dir",
            dbt_profile_dir,
            "--project-dir",
            dbt_project_dir,
        ],
        capture_output=True,
    )
    run_result.check_returncode()


def _get_db_objects_from_manifest(path: Path = Path("dbt/target/manifest.json")):
    if not path.exists():
        raise FileNotFoundError(f"Manifest file not found at {path}")
    manifest = json.loads(path.read_text())
    databases = set()
    dbt_tables = set()

    for node in manifest["nodes"].values():
        if node["resource_type"] in ["model", "snapshot", "seed"]:
            fqn = node["relation_name"].lower()
            dbt_tables.add(fqn)
            databases.add(node["database"])
    for source in manifest["sources"].values():
        if source["resource_type"] == "source":
            fqn = source["relation_name"].lower()
            dbt_tables.add(fqn)
            databases.add(source["database"])
    return dbt_tables, databases


def _dispose_table_query_builder(tables: list[dict], removal_month: str) -> list[str]:
    queries = []
    backup_date = datetime.date.today().strftime("%Y%m%d")
    for table in tables:
        table_name = table["name"]
        new_table_name = f"{table_name}_bck_{backup_date}_drp_{removal_month}"
        q = f"alter table {table_name} rename to {new_table_name};"
        queries.append(q)
    return queries


def mark_objects_for_removal(
    dbt_project_dir: str = "dbt",
    dbt_target: str = "prod",
    dbt_profile_dir: str = "dbt",
    ignore_table: list[str] = [],
    schema: list[str] = [],
):
    _validate_program("dbt")
    _create_dbt_manifest(
        dbt_project_dir=dbt_project_dir,
        dbt_profile_dir=dbt_profile_dir,
        dbt_target=dbt_target,
    )
    dbt_tables, databases = _get_db_objects_from_manifest()
    dbt_tables_not_transient = set(
        table.removesuffix("__transient") for table in dbt_tables
    )
    databases = sorted(databases)
    selected_databases = questionary.checkbox(
        "Which databases do you want to inspect?",
        choices=databases,
    ).ask()
    if not selected_databases:
        print("Aborting...")
        return
    existing_schemas = []
    with _snow_connection() as cursor:
        for database in selected_databases:
            query = f"select catalog_name, schema_name from {database}.information_schema.schemata where schema_name not in ('PUBLIC', 'INFORMATION_SCHEMA')"
            cursor.execute(query)
            result = cursor.fetchall()
            if not result:
                print(f"Database {database} does not exist or is empty.")
                continue
            for row in result:
                existing_schemas.append(
                    f"{row['CATALOG_NAME']}.{row['SCHEMA_NAME']}".lower()
                )
    existing_schemas.sort()
    existing_schemas = [schema for schema in existing_schemas if "drp" not in schema]
    default_schemas = []
    for schema_name in existing_schemas:
        if "meta" in schema_name:
            choice = Choice(schema_name)
            default_schemas.append(choice)
            continue
        if "policies" in schema_name:
            choice = Choice(schema_name)
            default_schemas.append(choice)
            continue
        if "alert" in schema_name:
            choice = Choice(schema_name)
            default_schemas.append(choice)
            continue
        if "task" in schema_name:
            choice = Choice(schema_name)
            default_schemas.append(choice)
            continue
        choice = Choice(schema_name, checked=True)
        default_schemas.append(choice)
    selected_schemas = questionary.checkbox(
        "Which schemas do you want to inspect?",
        choices=default_schemas,
    ).ask()
    if not selected_schemas:
        print("Aborting...")
        return
    selected_schemas = [
        f"'{selected_schemas.split('.')[1].upper()}'"
        for selected_schemas in selected_schemas
    ]
    existing_table = []
    with _snow_connection() as cursor:
        print(f"Fetching tables in databases: {selected_databases}")
        for database in selected_databases:
            query = f"select table_catalog, table_schema, table_name, last_altered from {database}.information_schema.tables where table_schema in ({','.join(selected_schemas)})"
            cursor.execute(query)
            result = cursor.fetchall()
            for row in result:
                existing_table.append(row)
    potential_drepcation_tables = []
    for table in existing_table:
        assert (
            table["TABLE_CATALOG"].lower() in selected_databases
        ), "not in {selected_databases}"
        if table["TABLE_SCHEMA"] == "PUBLIC":
            continue
        if table["TABLE_SCHEMA"] == "INFORMATION_SCHEMA":
            continue
        db_table = f"{table['TABLE_CATALOG']}.{table['TABLE_SCHEMA']}.{table['TABLE_NAME']}".lower()
        if db_table in dbt_tables:
            continue
        if db_table in dbt_tables_not_transient:
            continue
        if "drp" in db_table:
            continue
        choice = Choice(
            title=f"{db_table}".ljust(110) + f"Last altered: {table['LAST_ALTERED']}",
            value=db_table,
        )
        potential_drepcation_tables.append(
            {"name": db_table, "last_altered": table["LAST_ALTERED"]}
        )
    if not potential_drepcation_tables:
        print("No tables found for deprecation.")
        return
    potential_drepcation_tables.sort(key=lambda x: x["name"])

    max_table_name_length: int = max(
        len(table["name"]) for table in potential_drepcation_tables
    )
    potential_drepcation_tables_choices = [
        Choice(
            title=f"{table['name']}".ljust(max_table_name_length + 8)
            + f"Last altered: {table['last_altered']}",
            value=table,
        )
        for table in potential_drepcation_tables
    ]
    selected_tables = questionary.checkbox(
        "Which tables do you want to deprecate?",
        choices=potential_drepcation_tables_choices,
    ).ask()
    if not selected_tables:
        print("No tables selected for deprecation.")
        return
    print("Selected tables for deprecation:")
    for table in selected_tables:
        print(table["name"])
    dispose = questionary.confirm("Do you want to dispose these tables?").ask()
    if not dispose:
        print("Aborting...")
        return
    date_today = datetime.date.today()
    current_year = date_today.year
    current_month = date_today.month
    removal_year_months_choices = []
    for i in range(1, 13):
        year = current_year
        month = current_month + i
        if current_month + i > 12:
            year = current_year + 1
            month = current_month + i - 12

        title = f"{year}-{month}"
        value = f"{year}{month}"
        if month < 10:
            title = f"{year}-0{month}"
            value = f"{year}0{month}"
        removal_year_months_choices.append(Choice(title=title, value=value))

    removal_year_month = questionary.select(
        "Select month for removal:",
        choices=removal_year_months_choices,
    ).ask()
    if not removal_year_month:
        print("Aborting ...")
        return
    dispose_queries = _dispose_table_query_builder(
        tables=selected_tables,
        removal_month=removal_year_month,
    )
    with _snow_connection() as cursor:
        for query in dispose_queries:
            cursor.execute(query)

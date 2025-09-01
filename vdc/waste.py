import datetime
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import questionary
import snowflake.connector
from questionary import Choice
from snowflake.connector import DictCursor

from vdc.utils import _validate_program, config


def _snow_connection():
    snowflake_config = config["snowflake"]

    return snowflake.connector.connect(**snowflake_config).cursor(DictCursor)


def _create_dbt_manifest(
    dbt_project_dir: str = "dbt", dbt_profile_dir: str = "dbt", dbt_target: str = "prod"
):

    run_result = subprocess.run(
        [
            "dbt",
            "deps",
            "--target",
            dbt_target,
            "--profiles-dir",
            dbt_profile_dir,
            "--project-dir",
            dbt_project_dir,
        ],
        capture_output=True,
    )
    if run_result.returncode != 0:
        print("Error running command:", run_result.stderr)
        print("Command output:", run_result.stdout)
        exit(1)
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
    if run_result.returncode != 0:
        print("Error running command:", run_result.stderr)
        print("Command output:", run_result.stdout)
        exit(1)


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


def _dispose_table_query_builder(
    tables: list[dict], removal_month: str, user_alias: str
) -> list[str]:
    queries = []
    backup_date = datetime.date.today().strftime("%Y%m%d")
    for table in tables:
        table_name = table["name"]
        new_table_name = (
            f"{table_name}_bck_{backup_date}_user_{user_alias}_drp_{removal_month}"
        )
        q = f"alter table {table_name} rename to {new_table_name};"
        queries.append(q)
    return queries


def _ask_about_database_and_schemas(databases) -> tuple[str]:
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

    return tuple(selected_schemas)


def mark_objects_for_removal(
    dbt_project_dir: str = "dbt",
    dbt_target: str = "prod",
    dbt_profile_dir: str = "dbt",
    dry_run: bool = False,
    ignore_tables: Optional[tuple[str]] = None,
    schemas: Optional[tuple[str]] = None,
):
    if ignore_tables:
        for table in ignore_tables:
            assert (
                len(table.split(".")) == 3
            ), "Table must be in the format 'database.schema.table'"
        ignore_tables = tuple(table.lower() for table in ignore_tables)

    if schemas:
        for schema in schemas:
            assert (
                len(schema.split(".")) == 2
            ), "Schema must be in the format 'database.schema'"
        schemas = tuple(schema.lower() for schema in schemas)

    _validate_program("dbt")
    _create_dbt_manifest(
        dbt_project_dir=dbt_project_dir,
        dbt_profile_dir=dbt_profile_dir,
        dbt_target=dbt_target,
    )
    dbt_tables, databases = _get_db_objects_from_manifest(
        path=Path(f"{dbt_project_dir}/target/manifest.json")
    )
    dbt_tables_not_transient = set(
        table.removesuffix("__transient") for table in dbt_tables
    )
    databases = sorted(databases)
    if not schemas:
        schemas = _ask_about_database_and_schemas(databases=databases)
    selected_databases = set(schema.split(".")[0] for schema in schemas)
    selected_schemas = set(f"'{schema.split('.')[1].upper()}'" for schema in schemas)

    if not selected_schemas:
        print("Aborting...")
        return

    existing_table = []
    with _snow_connection() as cursor:
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
        if ignore_tables and db_table in ignore_tables:
            continue
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
        print("No potential tables found.")
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

    if dry_run:
        print("Potential tables to mark for removal:")
        for table in potential_drepcation_tables_choices:
            print(table.title)

    if not dry_run:
        selected_tables = questionary.checkbox(
            "Which tables do you want to deprecate?",
            choices=potential_drepcation_tables_choices,
        ).ask()
        if not selected_tables:
            print("No tables selected for disposal.")
            return
        print("Selected tables for disposal:")
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
            user_alias=config.get("user_alias", "unknown"),
        )
        with _snow_connection() as cursor:
            for query in dispose_queries:
                cursor.execute(query)


def _get_marked_objects():
    with _snow_connection() as cursor:
        q = f"show databases like '%drp%' in account"
        cursor.execute(q)
        databases = cursor.fetchall()
        cursor.execute(f"show schemas like '%drp%' in account")
        schemas = cursor.fetchall()
        cursor.execute(f"show tables like '%drp%' in account")
        tables = cursor.fetchall()
        cursor.execute(f"show views like '%drp%' in account")
        views = cursor.fetchall()
    return databases, schemas, tables, views


def _is_potential_drp_object(object_name: str, compare_date: datetime.date) -> bool:
    drp_month = object_name.rsplit("DRP_")[-1]
    if len(drp_month) != 6:
        drp_month = object_name.rsplit("DRP")[-1]
    if len(drp_month) != 6:
        print(
            f"Invalid month format in marked object. Expected format: DRP_YYYYMM: {object_name}"
        )
        return True
    db_date = datetime.date(
        year=int(drp_month[:4]),
        month=int(drp_month[4:6]),
        day=1,
    )
    if db_date < compare_date:
        return True
    return False


def _filter_objects_for_removal(
    databases, schemas, tables, views, compare_date: datetime.date
):
    potential_drp_databases = []
    for database in databases:
        database_name = f"{database['name']}"
        if _is_potential_drp_object(
            object_name=database_name, compare_date=compare_date
        ):
            potential_drp_databases.append(database_name)

    potential_drp_schemas = []
    for schema in schemas:
        schema_name = f"{schema['database_name']}.{schema['name']}"
        if _is_potential_drp_object(object_name=schema_name, compare_date=compare_date):
            potential_drp_schemas.append(schema_name)

    potential_drp_tables = []
    for table in tables:
        table_name = f"{table['database_name']}.{table['schema_name']}.{table['name']}"
        if _is_potential_drp_object(object_name=table_name, compare_date=compare_date):
            potential_drp_tables.append(table_name)

    potential_drp_views = []
    for view in views:
        view_name = f"{view['database_name']}.{view['schema_name']}.{view['name']}"
        if _is_potential_drp_object(object_name=view_name, compare_date=compare_date):
            potential_drp_views.append(view_name)
    return (
        potential_drp_databases,
        potential_drp_schemas,
        potential_drp_tables,
        potential_drp_views,
    )


def _drop_object_query_builder(
    databases: list[str],
    schemas: list[str],
    tables: list[str],
    views: list[str],
) -> list[str]:
    queries = []
    if databases:
        for database in databases:
            q = f"drop database {database}"
            queries.append(q)
    if schemas:
        for schema in schemas:
            q = f"drop schema {schema}"
            queries.append(q)
    if tables:
        for table in tables:
            q = f"drop table {table}"
            queries.append(q)
    if views:
        for view in views:
            q = f"drop view {view}"
            queries.append(q)
    return queries


def remove_marked_objects(dry_run: bool):
    compare_date = datetime.date.today()
    databases, schemas, tables, views = _get_marked_objects()
    (
        potential_drp_databases,
        potential_drp_schemas,
        potential_drp_tables,
        potential_drp_views,
    ) = _filter_objects_for_removal(
        databases=databases,
        schemas=schemas,
        tables=tables,
        views=views,
        compare_date=compare_date,
    )
    if (
        not potential_drp_databases
        and not potential_drp_schemas
        and not potential_drp_tables
        and not potential_drp_views
    ):
        print("No objects found for removal.")
        return
    if dry_run:
        print("=======================================================")
        print("\nPotential objects for removal:\n")
        if potential_drp_databases:
            print("Databases:")
            for database in potential_drp_databases:
                print(database)
            print("")
        if potential_drp_schemas:
            print("Schemas:")
            for schema in potential_drp_schemas:
                print(schema)
            print("")
        if potential_drp_tables:
            print("Tables:")
            for table in potential_drp_tables:
                print(table)
            print("")
        if potential_drp_views:
            print("Views:")
            for view in potential_drp_views:
                print(view)
            print("")
        return

    remove_databases = None
    remove_schemas = None
    remove_tables = None
    remove_views = None
    if potential_drp_databases:
        remove_databases = questionary.checkbox(
            "Select which databases do you want to remove",
            choices=potential_drp_databases,
        ).ask()
    if potential_drp_schemas:
        drop_databases = set()
        for potential_drp_schema in potential_drp_schemas:
            db_name, schema_name = potential_drp_schema.split(".")
            if db_name in remove_databases:
                drop_databases.add(potential_drp_schema)
        schema_choices = list(set(potential_drp_schemas) - drop_databases)
        remove_schemas = questionary.checkbox(
            "Select which schemas do you want to remove",
            choices=schema_choices,
        ).ask()
    if potential_drp_tables:
        drop_schemas = set()
        for potential_drp_table in potential_drp_tables:
            db_name, schema_name, table_name = potential_drp_table.split(".")
            if db_name in remove_databases:
                drop_schemas.add(potential_drp_table)
                continue
            if f"{db_name}.{schema_name}" in remove_schemas:
                drop_schemas.add(potential_drp_table)
                continue
        table_choices = list(set(potential_drp_tables) - drop_schemas)
        remove_tables = questionary.checkbox(
            "Select which tables do you want to remove",
            choices=table_choices,
        ).ask()
    if potential_drp_views:
        drop_schemas = set()
        for potential_drp_view in potential_drp_views:
            db_name, schema_name, view_name = potential_drp_view.split(".")
            if db_name in remove_databases:
                drop_schemas.add(potential_drp_view)
                continue
            if f"{db_name}.{schema_name}" in remove_schemas:
                drop_schemas.add(potential_drp_view)
                continue
        view_choices = list(set(potential_drp_views) - drop_schemas)
        remove_views = questionary.checkbox(
            "Select which views do you want to remove",
            choices=view_choices,
        ).ask()
    if (
        not remove_databases
        and not remove_schemas
        and not remove_tables
        and not remove_views
    ):
        print("No objects selected for removal.")
        return
    print("Selected objects for removal:")
    if remove_databases:
        for database in remove_databases:
            print(database)
    if remove_schemas:
        for schema in remove_schemas:
            print(schema)
    if remove_tables:
        for table in remove_tables:
            print(table)
    if remove_views:
        for view in remove_views:
            print(view)
    remove = questionary.confirm(
        "Do you want to remove these objects? This action is irreversible.",
        default=False,
    ).ask()
    if not remove:
        print("Aborting...")
        return
    print("Dropping objects...")
    drop_queries = _drop_object_query_builder(
        databases=remove_databases,
        schemas=remove_schemas,
        tables=remove_tables,
        views=remove_views,
    )
    with _snow_connection() as cursor:
        for query in drop_queries:
            cursor.execute(query)
    print("Objects removed.")
    print("Done.")
    return

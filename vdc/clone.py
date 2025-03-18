import logging

import snowflake.connector
from snowflake.connector import DictCursor

LOGGER = logging.getLogger(__file__)


def _snow_config():
    return {
        "user": os.environ["DBT_USR"],
        "authenticator": "externalbrowser",
        "account": "wx23413.europe-west4.gcp",
        "role": "sysadmin",
        "warehouse": "dev__xs",
    }


class SnowflakeConnector:
    def __init__(self):
        with snowflake.connector.connect(**_snow_config()) as ctx:
            self.cur = ctx.cursor(DictCursor)

    def run_query(self, query: str) -> list[str]:
        result = self.cur.execute(query)
        return result


def create_db_clone(src: str, dst: str, usage: tuple[str]):
    prod_db = src
    clone_db = dst

    use_role = "use role sysadmin"
    create_sql = f"create or replace database {clone_db} clone {prod_db}"
    show_dynamic_tables = f"show dynamic tables in database {clone_db}"

    try:
        conn = SnowflakeConnector()
    except Exception as e:
        LOGGER.error(f"Error creating Snowflake connection. {e}")
        return

    conn.run_query(use_role)
    conn.run_query(create_sql)
    dynamic_tables = conn.run_query(show_dynamic_tables)
    for suspend_dynamic_table in _suspend_dynamic_tables(
        db=clone_db, dynamic_tables=dynamic_tables
    ):
        conn.run_query(suspend_dynamic_table)
    for grant_usage_to_role in _grant_usage(db=clone_db, roles=usage):
        conn.run_query(grant_usage_to_role)


def _suspend_dynamic_tables(db, dynamic_tables: list[dict]) -> list[str]:
    sql = []
    for dynamic_table in dynamic_tables:
        if dynamic_table["scheduling_state"] != "SUSPENDED":
            schema = dynamic_table["schema_name"]
            table = dynamic_table["name"]
            sql.append(f"alter dynamic table {db}.{schema}.{table} suspend")
    return sql


def _grant_usage(db, roles: list[str]):
    return [f"grant usage on database {db} to role {role}" for role in roles]

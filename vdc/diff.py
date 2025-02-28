import os
import sys

import pandas as pd
import snowflake.connector


# Snowflake-config
def _snow_config():
    return {
        "user": os.environ["DBT_USR"],
        "authenticator": "externalbrowser",
        "account": "wx23413.europe-west4.gcp",
        "role": "sysadmin",
        "warehouse": "dev__xs",
    }


def _fetch_diff(query):
    with snowflake.connector.connect(**_snow_config()) as ctx:
        cur = ctx.cursor()
        cur.execute(query)
        return cur.fetch_pandas_all()


def _query_builder(database, dev_database, schema, table, primary_key):
    order_by = f"{primary_key},db_env"

    query = f"""
    select '{database}' as db_env, * from {database}.{schema}.{table}
    except
    select '{database}' as db_env, * from {dev_database}.{schema}.{table}
    union all
    select '{dev_database}' as db_env, * from {dev_database}.{schema}.{table}
    except
    select '{dev_database}' as db_env, * from {database}.{schema}.{table}
    order by {order_by}
    """
    return query


def table_diff(table, primary_key):
    database, schema, table = table.upper().split(".")
    primary_key = primary_key.upper()

    dev_database = f"dev_{os.environ['USER']}_{database}"

    pd.set_option("display.max_rows", None)  # Set to None to display all rows
    pd.set_option("display.max_columns", None)  # Set to None to display all columns

    query = _query_builder(database, dev_database, schema, table, primary_key)

    print("Running query:")
    print(query)
    print("")

    df = _fetch_diff(query)
    prod_db = (
        df.query(f"DB_ENV == '{database}'")
        .drop(columns=["DB_ENV"])
        .set_index(primary_key)
    )
    print(f"Prod: {len(prod_db)} rows")

    dev_db = (
        df.query(f"DB_ENV == '{dev_database}'")
        .drop(columns=["DB_ENV"])
        .set_index(primary_key)
    )
    print(f"Dev: {len(dev_db)} rows")
    print("")

    print("Diff:")
    diff = prod_db.compare(
        other=dev_db, align_axis=0, result_names=(database, dev_database)
    )
    print(diff)

    generate_report = input("Vil du lage excel-rapport? y/N:").lower() == "y"
    if generate_report:
        dagens_dato = pd.Timestamp.now().strftime("%Y-%m-%d")
        file_name = f"diff_{table.lower()}_{dagens_dato}.xlsx"
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            diff.to_excel(writer, sheet_name="diff", merge_cells=False)
            worksheet = writer.sheets["diff"]
        print(f"Excel-rapport lagret som {file_name}")

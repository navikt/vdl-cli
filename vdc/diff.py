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


def _fetch_diff(prod_query, dev_query):
    with snowflake.connector.connect(**_snow_config()) as ctx:
        cur = ctx.cursor()
        cur.execute(prod_query)
        prod_df = cur.fetch_pandas_all()

        cur.execute(dev_query)
        dev_df = cur.fetch_pandas_all()
        return prod_df, dev_df


def _query_builder(database, other_database, schema, table, primary_key):
    return f"""
    select * from {database}.{schema}.{table}
    except
    select  * from {other_database}.{schema}.{table}
    order by {primary_key}
    """


def _compare_df(prod_df, dev_df, prod_name, dev_name):
    return prod_df.compare(
        other=dev_df, align_axis=0, result_names=(prod_name, dev_name)
    )


def table_diff(table, primary_key, fetch_diff=_fetch_diff, ci=False):
    database, schema, table = table.upper().split(".")
    primary_key = primary_key.upper()

    dev_database = f"dev_{os.environ['USER']}_{database}"

    pd.set_option("display.max_rows", None)  # Set to None to display all rows
    pd.set_option("display.max_columns", None)  # Set to None to display all columns

    prod_query = _query_builder(database=database, other_database=dev_database, schema=schema, table=table, primary_key=primary_key)
    dev_query = _query_builder(database=dev_database, other_database=database, schema=schema, table=table, primary_key=primary_key)

    print("Running query:")
    print(prod_query)
    print("")
    print(dev_query)
    print("")

    prod_df, dev_df = fetch_diff(prod_query=prod_query, dev_query=dev_query)
    prod_df = prod_df.set_index(primary_key)
    dev_df = dev_df.set_index(primary_key)

    print(f"Prod: {len(prod_df)} rows")
    print(f"Dev: {len(dev_df)} rows")
    print("")

    if prod_df.equals(dev_df):
        print("No diff")
        return

    diff = _compare_df(prod_df=prod_df, dev_df=dev_df, prod_name="prod", dev_name="dev")

    if ci:
        return diff

    preview_diff = input("Preview diff? y/N:").lower() == "y"
    if preview_diff:
        print("Diff:")
        print(diff)
        print("")

    generate_report = input("Export to excel? y/N:").lower() == "y"
    if generate_report:
        dagens_dato = pd.Timestamp.now().strftime("%Y-%m-%d")
        file_name = f"diff_{table.lower()}_{dagens_dato}.xlsx"
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            diff.to_excel(writer, sheet_name="diff", merge_cells=False)
            worksheet = writer.sheets["diff"]
        print(f"Excel-report stored as: {file_name}")

import os
from typing import Optional

import pandas as pd
import snowflake.connector

from vdc.utils import _spinner


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
    with _spinner("Fetching data"):
        with snowflake.connector.connect(**_snow_config()) as ctx:
            cur = ctx.cursor()
            cur.execute(prod_query)
            prod_df = cur.fetch_pandas_all()

            cur.execute(dev_query)
            dev_df = cur.fetch_pandas_all()
            return prod_df, dev_df


def _query_builder(table: str, compare_to: str) -> list[str]:
    return [
        f"""
            select * from {table}
            except
            select * from {compare_to}
        """,
        f"""
            select * from {compare_to}
            except
            select * from {table}
        """,
    ]


def _compare_df(prod_df, dev_df, prod_name, dev_name, primary_key):
    prod_df = prod_df.set_index(primary_key).sort_index()
    dev_df = dev_df.set_index(primary_key).sort_index()

    prod_diff = prod_df.index.difference(dev_df.index)
    dev_diff = dev_df.index.difference(prod_df.index)

    df1 = prod_df.reindex(prod_df.index.values.tolist() + dev_diff.values.tolist())
    df2 = dev_df.reindex(dev_df.index.values.tolist() + prod_diff.values.tolist())

    return df1.compare(other=df2, align_axis=0, result_names=(prod_name, dev_name))


def table_diff(table, primary_key, compare_to):
    primary_key = primary_key.upper()

    pd.set_option("display.max_rows", None)  # Set to None to display all rows
    pd.set_option("display.max_columns", None)  # Set to None to display all columns

    prod_query, dev_query = _query_builder(
        table=table,
        compare_to=compare_to,
    )

    print("Running query:")
    print(prod_query)
    print("and")
    print(dev_query)
    print("")

    prod_df, dev_df = _fetch_diff(prod_query=prod_query, dev_query=dev_query)

    print(f"Prod: {len(prod_df)} rows")
    print(f"Dev: {len(dev_df)} rows")
    print("")

    if len(prod_df) == 0 and len(dev_df) == 0:
        print("No diff")
        return

    diff = _compare_df(
        prod_df=prod_df,
        dev_df=dev_df,
        prod_name="prod",
        dev_name="dev",
        primary_key=primary_key,
    )

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

import os
from typing import Optional

import pandas as pd
import snowflake.connector
from snowflake.connector import DictCursor

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


def _query_builder(
    table: str,
    compare_to: str,
    columns: Optional[tuple],
    ignore_columns: Optional[tuple],
    primary_key: str,
    table_desc: list[dict],
    compare_to_desc: list[dict],
) -> list[str]:
    unique_columns = None
    if columns:
        unique_columns = set(columns + (primary_key,))
    cols = "*" if not unique_columns else ", ".join(unique_columns)
    exclude_cols_table = None
    exclude_cols_compare_to = None
    if ignore_columns:
        exclude_cols_table = set()
        exclude_cols_compare_to = set()
        table_column = [t["name"].lower() for t in table_desc]
        compare_to_column = [t["name"].lower() for t in compare_to_desc]
        for col in ignore_columns:
            col = col.lower()
            if col in table_column:
                exclude_cols_table.add(col)
            if col in compare_to_column:
                exclude_cols_compare_to.add(col)
        exclude_cols_table = ", ".join(exclude_cols_table)
        exclude_cols_compare_to = ", ".join(exclude_cols_compare_to)

    selected_cols_table = (
        f"{cols} exclude({exclude_cols_table})" if exclude_cols_table else cols
    )
    selected_cols_compare_to = (
        f"{cols} exclude({exclude_cols_compare_to})"
        if exclude_cols_compare_to
        else cols
    )
    return [
        f"""
            select {selected_cols_table} from {table}
            except
            select {selected_cols_compare_to} from {compare_to}
        """,
        f"""
            select {selected_cols_compare_to} from {compare_to}
            except
            select {selected_cols_table} from {table}
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


def _desc(table: str) -> list[dict]:
    with snowflake.connector.connect(**_snow_config()) as ctx:
        cur = ctx.cursor(DictCursor)
        cur.execute(f"desc table {table}")
        return cur.fetchall()


def table_diff(table, primary_key, compare_to, columns, ignore_columns):
    primary_key = primary_key.upper()

    pd.set_option("display.max_rows", None)  # Set to None to display all rows
    pd.set_option("display.max_columns", None)  # Set to None to display all columns
    table_desc = _desc(table=table)
    compare_to_desc = _desc(table=compare_to)
    prod_query, dev_query = _query_builder(
        table=table,
        compare_to=compare_to,
        columns=columns,
        ignore_columns=ignore_columns,
        primary_key=primary_key,
        table_desc=table_desc,
        compare_to_desc=compare_to_desc,
    )

    print("Running query:")
    print(prod_query)
    print("and")
    print(dev_query)
    print("")

    prod_df, dev_df = _fetch_diff(prod_query=prod_query, dev_query=dev_query)

    print("\nRows different or missing in other table:")
    print(f"{table}:".ljust(45) + f"{len(prod_df)}".rjust(10) + " rows")
    print(f"{compare_to}:".ljust(45) + f"{len(dev_df)}".rjust(10) + " rows")
    print("")

    if len(prod_df) == 0 and len(dev_df) == 0:
        print("No diff")
        return

    diff = _compare_df(
        prod_df=prod_df,
        dev_df=dev_df,
        prod_name=table,
        dev_name=compare_to,
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

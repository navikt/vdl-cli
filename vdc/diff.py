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
    table_column = set(t["name"].lower() for t in table_desc)
    compare_to_column = set(t["name"].lower() for t in compare_to_desc)
    unique_columns = table_column.intersection(compare_to_column)
    if columns:
        columns = tuple(c.lower() for c in columns)
        unique_columns = set(columns + (primary_key.lower(),))

    if ignore_columns:
        ignore_columns = tuple(c.lower() for c in ignore_columns)
        unique_columns = unique_columns - set(ignore_columns)

    cols = ",\n".join(unique_columns)
    return [
        f"select\n{cols}\nfrom {table}\nexcept\nselect\n{cols}\nfrom {compare_to}",
        f"select\n{cols}\nfrom {compare_to}\nexcept\nselect\n{cols}\nfrom {table}",
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


def _remove_tz_from_timestamp_in_df(
    df: pd.DataFrame, timezone: str = "Europe/Oslo"
) -> pd.DataFrame:
    print("Removing timezone from datetime columns...")
    for col in df.select_dtypes(include=[f"datetime64[ns, {timezone}]"]):
        df[col] = df[col].dt.tz_localize(None)
        print(f"Removed timezone from column: {col}")
    return df


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
        diff = _remove_tz_from_timestamp_in_df(diff)
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            diff.to_excel(writer, sheet_name="diff", merge_cells=False)
            worksheet = writer.sheets["diff"]
        print(f"Excel-report stored as: {file_name}")

import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner

import pandas as pd

from vdc.diff import _compare_df, _query_builder


class TestTableDiff(unittest.TestCase):

    def test_query_limits_results_after_except_and_normalizes_keys(self):
        queries = _query_builder(
            table="db.marts.fak_faktura",
            compare_to="dev.marts.fak_faktura_oppfolging",
            columns=None,
            ignore_columns=None,
            primary_key="PK_FAK_FAKTURA",
            compare_to_primary_key="PK_FAK_FAKTURA_OPPFOLGING",
            table_desc=[{"name": "PK_FAK_FAKTURA"}, {"name": "VALUE"}],
            compare_to_desc=[
                {"name": "PK_FAK_FAKTURA_OPPFOLGING"}, {"name": "VALUE"}
            ],
        )
        for query in queries:
            self.assertEqual(query.count("limit 500"), 1)
            self.assertTrue(query.endswith("\nlimit 500"))
            self.assertFalse(query.startswith("select * from ("))
            self.assertIn("\norder by pk_fak_faktura\nlimit 500", query)
            self.assertIn("\nexcept\n", query)
            self.assertIn("pk_fak_faktura::varchar as pk_fak_faktura", query)
            self.assertIn(
                "pk_fak_faktura_oppfolging::varchar as pk_fak_faktura", query
            )

    @patch.dict(os.environ, {"DBT_USR": "test", "USER": "test"})
    def test_cli_primary_key_is_optional(self):
        from vdc.main import cli

        with patch("vdc.diff.table_diff") as table_diff:
            result = CliRunner().invoke(cli, [
                "diff", "faktura.marts.fak_faktura",
                "--compare-to-table", "fak_faktura_oppfolging",
            ])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIsNone(table_diff.call_args.kwargs["primary_key"])
        self.assertTrue(table_diff.call_args.kwargs["compare_to"].endswith(
            ".marts.fak_faktura_oppfolging"
        ))

    @patch.dict(os.environ, {"DBT_USR": "test", "USER": "test"})
    def test_cli_explicit_primary_key(self):
        from vdc.main import cli

        with patch("vdc.diff.table_diff") as table_diff:
            result = CliRunner().invoke(cli, [
                "diff", "faktura.marts.fak_faktura", "--primary-key", "id",
            ])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(table_diff.call_args.kwargs["primary_key"], "id")

    def test_compare_df_with_no_diff(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        dev_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        result = _compare_df(prod_df, dev_df, "prod", "dev", "a")

        self.assertTrue(result.empty)

    def test_compare_df_with_diff(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        dev_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 7]})

        result = _compare_df(prod_df, dev_df, "prod", "dev", "a")
        expected = pd.DataFrame(
            {"a": [3, 3], "b": [6.0, 7.0], "result_name": ["prod", "dev"]}
        ).set_index(["a", "result_name"])
        self.assertTrue(result.equals(expected))

    def test_compare_df_with_one_more_row_in_prod(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        dev_df = pd.DataFrame({"a": [1, 2], "b": [4, 5]})

        result = _compare_df(prod_df, dev_df, "prod", "dev", "a")
        expected = pd.DataFrame(
            {"a": [3, 3], "b": [6.0, None], "result_name": ["prod", "dev"]}
        ).set_index(["a", "result_name"])
        self.assertTrue(result.equals(expected))

    def test_compare_df_with_one_more_row_in_dev(self):
        prod_df = pd.DataFrame({"a": [1, 2], "b": [4, 5]})
        dev_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        result = _compare_df(prod_df, dev_df, "prod", "dev", "a")
        expected = pd.DataFrame(
            {"a": [3, 3], "b": [None, 6.0], "result_name": ["prod", "dev"]}
        ).set_index(["a", "result_name"])
        self.assertTrue(result.equals(expected))

    def test_compare_df_underscore_in_column_name(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b_c": [4, 5, 6]})
        dev_df = pd.DataFrame({"a": [1, 2, 3], "b_c": [4, 5, 7]})

        result = _compare_df(prod_df, dev_df, "prod", "dev", "a")
        expected = pd.DataFrame(
            {"a": [3, 3], "b_c": [6.0, 7.0], "result_name": ["prod", "dev"]}
        ).set_index(["a", "result_name"])
        self.assertTrue(result.equals(expected))

    def test_compare_df_not_sorted_by_primary_key(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        dev_df = pd.DataFrame({"a": [3, 1, 2], "b": [6, 4, 5]})

        result = _compare_df(prod_df, dev_df, "prod", "dev", "a")
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()

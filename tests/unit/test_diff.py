import os
import unittest

import pandas as pd

from vdc.diff import _compare_df, _query_builder


class TestTableDiff(unittest.TestCase):

    def test_query_limits_results_after_except(self):
        queries = _query_builder(
            table="db.marts.fak_faktura",
            compare_to="dev.marts.fak_faktura",
            columns=None,
            ignore_columns=None,
            primary_key="PK_FAK_FAKTURA",
            table_desc=[{"name": "PK_FAK_FAKTURA"}, {"name": "VALUE"}],
            compare_to_desc=[{"name": "PK_FAK_FAKTURA"}, {"name": "VALUE"}],
        )
        for query in queries:
            self.assertEqual(query.count("limit 500"), 1)
            self.assertTrue(query.endswith("\norder by pk_fak_faktura\nlimit 500"))
            self.assertFalse(query.startswith("select * from ("))
            self.assertIn("\nexcept\n", query)

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

import os
import unittest

import pandas as pd

from vdc.diff import _compare_df, _query_builder


class TestTableDiff(unittest.TestCase):

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

    def test_query_builder(self):
        table = "database.schema.table"
        other_database = "other_database"
        q1, q2 = _query_builder(
            table=table,
            other_database=other_database,
        )
        result = [line.strip() for line in q1.split("\n")]
        result.extend([line.strip() for line in q2.split("\n")])
        print(result)
        expected = [
            "",
            "select * from database.schema.table",
            "except",
            "select * from other_database.schema.table",
            "",
            "",
            "select * from other_database.schema.table",
            "except",
            "select * from database.schema.table",
            "",
        ]
        self.assertEqual(result, expected)

    def test_query_builder_with_no_other_database(self):
        original_user = os.environ.get("USER")
        os.environ["USER"] = "user"

        table = "database.schema.table"
        q1, q2 = _query_builder(
            table=table,
            other_database=None,
        )
        result = [line.strip() for line in q1.split("\n")]
        result.extend([line.strip() for line in q2.split("\n")])
        print(result)
        expected = [
            "",
            "select * from database.schema.table",
            "except",
            "select * from dev_user_database.schema.table",
            "",
            "",
            "select * from dev_user_database.schema.table",
            "except",
            "select * from database.schema.table",
            "",
        ]

        os.environ["USER"] = original_user
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()

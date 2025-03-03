import os
import unittest
import pandas as pd
from vdc.diff import _compare_df


class TestTableDiff(unittest.TestCase):

    def test_compare_df_with_no_diff(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        dev_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        result = _compare_df(prod_df, dev_df, "prod", "dev")

        self.assertTrue(result.empty)

    def test_compare_df_with_diff(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}).set_index("a")
        dev_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 7]}).set_index("a")

        result = _compare_df(prod_df, dev_df, "prod", "dev")
        expected = (
            pd.DataFrame({"a": [3, 3], "b": [6.0, 7.0], "result_name": ["prod", "dev"]})
            .set_index(["a", "result_name"])
        )
        self.assertTrue(result.equals(expected))

    def test_compare_df_with_one_more_row_in_prod(self):
        prod_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}).set_index("a")
        dev_df = pd.DataFrame({"a": [1, 2], "b": [4, 5]}).set_index("a")

        result = _compare_df(prod_df, dev_df, "prod", "dev")
        expected = (
            pd.DataFrame({"a": [3], "b": [6.0], "result_name": ["prod"]})
            .set_index(["a", "result_name"])
        )
        self.assertTrue(result.equals(expected))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import csv
import io
import json
import os
import tempfile
import unittest

import csv_union as cu


SAMPLES = os.path.join(os.path.dirname(__file__), "samples")
FILE_A = os.path.join(SAMPLES, "orders_a.csv")
FILE_B = os.path.join(SAMPLES, "orders_b.csv")


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    old_out, old_err = cu.sys.stdout, cu.sys.stderr
    cu.sys.stdout, cu.sys.stderr = stdout, stderr
    try:
        code = cu.main(argv)
    finally:
        cu.sys.stdout, cu.sys.stderr = old_out, old_err
    err = stderr.getvalue()
    summary = json.loads(err) if err.strip().startswith("{") else None
    return code, stdout.getvalue(), summary, err


class HelperTests(unittest.TestCase):
    def test_union_headers_preserves_first_seen_order(self):
        self.assertEqual(
            cu.union_headers(
                [["order_id", "customer", "amount"], ["order_id", "customer", "amount", "currency"]]
            ),
            ["order_id", "customer", "amount", "currency"],
        )


class CliTests(unittest.TestCase):
    def test_sample_union(self):
        code, out, summary, _err = run_main([FILE_A, FILE_B])
        self.assertEqual(code, 0)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["output_rows"], 4)
        self.assertEqual(summary["output_columns"], ["order_id", "customer", "amount", "currency"])
        self.assertEqual(summary["files"][0]["missing_columns"], ["currency"])
        self.assertEqual(summary["files"][1]["missing_columns"], [])
        rows = list(csv.DictReader(io.StringIO(out)))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["order_id"], "1001")
        self.assertEqual(rows[0]["currency"], "")
        self.assertEqual(rows[2]["currency"], "AED")
        self.assertEqual(rows[3]["customer"], "Lee")

    def test_strict_fails_on_schema_diff(self):
        code, out, summary, _err = run_main([FILE_A, FILE_B, "--strict"])
        self.assertEqual(code, 1)
        self.assertFalse(summary["ok"])
        self.assertEqual(out, "")
        self.assertTrue(any("strict" in item for item in summary["failed_checks"]))

    def test_source_col_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "out.csv")
            code, out, summary, _err = run_main(
                [FILE_A, FILE_B, "--source-col", "_source", "--write", dest]
            )
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            self.assertEqual(summary["output_columns"][-1], "_source")
            with open(dest, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["_source"], FILE_A)
            self.assertEqual(rows[2]["_source"], FILE_B)

    def test_identical_schemas_ok_strict(self):
        code, out, summary, _err = run_main([FILE_A, FILE_A, "--strict"])
        self.assertEqual(code, 0)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["output_rows"], 4)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(out)))), 4)

    def test_missing_file_exits_two(self):
        code, _out, summary, err = run_main([FILE_A, "/tmp/does-not-exist-csv-union.csv"])
        self.assertEqual(code, 2)
        self.assertIsNone(summary)
        self.assertIn("csv-union:", err)


if __name__ == "__main__":
    unittest.main()

# csv-union

Concatenate several CSV files into one, even when the headers do not match.

The output header is the union of every input, in first-seen column order.
A file that is missing a column gets a blank; a file that has extra columns
keeps them. A JSON summary of row counts and schema differences is printed
to stderr. `--strict` fails if any file's columns differ from the first file.
`--source-col` adds a column that records which file each row came from.

Standard library only. Requires Python 3.

## How to run

```bash
python3 csv_union.py samples/orders_a.csv samples/orders_b.csv
```

Write the combined file instead of printing it:

```bash
python3 csv_union.py samples/orders_a.csv samples/orders_b.csv --write combined.csv
```

Fail when schemas differ:

```bash
python3 csv_union.py samples/orders_a.csv samples/orders_b.csv --strict
```

Tag each row with its source path:

```bash
python3 csv_union.py samples/orders_a.csv samples/orders_b.csv --source-col _source
```

Run the tests:

```bash
python3 -m unittest -v
```

## Example output

From a real run of `python3 csv_union.py samples/orders_a.csv samples/orders_b.csv`.
The JSON is written to stderr; the CSV is written to stdout.

```
{
  "files": [
    {
      "path": "samples/orders_a.csv",
      "rows": 2,
      "columns": [
        "order_id",
        "customer",
        "amount"
      ],
      "missing_columns": [
        "currency"
      ],
      "extra_columns": []
    },
    {
      "path": "samples/orders_b.csv",
      "rows": 2,
      "columns": [
        "order_id",
        "customer",
        "amount",
        "currency"
      ],
      "missing_columns": [],
      "extra_columns": []
    }
  ],
  "output_columns": [
    "order_id",
    "customer",
    "amount",
    "currency"
  ],
  "output_rows": 4,
  "written": "-",
  "ok": true
}
order_id,customer,amount,currency
1001,Ali,50.00,
1002,Neha,20.00,
1003,Sam,80.00,AED
1004,Lee,15.50,INR
```

`orders_a.csv` has no `currency` column, so those two rows are blank in the
combined output. `--strict` on the same files exits 1 and writes no CSV.

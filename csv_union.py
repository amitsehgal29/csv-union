#!/usr/bin/env python3
"""csv-union: concatenate CSVs, aligning columns that don't match.

Standard library only. Headers are the union of every file, in first-seen
order. A file that is missing a column gets a blank; extra columns are kept.
A JSON summary of row counts and schema differences goes to stderr.
"""
import argparse
import csv
import json
import sys


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], []
        return list(reader.fieldnames), list(reader)


def union_headers(file_headers):
    seen = []
    for headers in file_headers:
        for name in headers:
            if name not in seen:
                seen.append(name)
    return seen


def align_rows(rows, headers, out_fields):
    aligned = []
    for row in rows:
        aligned.append({name: row.get(name, "") if row.get(name) is not None else "" for name in out_fields})
    return aligned


def describe_file(path, headers, rows, out_fields):
    header_set = set(headers)
    out_set = set(out_fields)
    return {
        "path": path,
        "rows": len(rows),
        "columns": headers,
        "missing_columns": [name for name in out_fields if name not in header_set],
        "extra_columns": [name for name in headers if name not in out_set],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Concatenate CSV files, filling missing columns so headers align."
    )
    parser.add_argument("paths", nargs="+", help="CSV files to union, in order")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail if any file's columns differ from the first file",
    )
    parser.add_argument(
        "--source-col",
        metavar="NAME",
        help="add a column with this name holding the source file path",
    )
    parser.add_argument(
        "--write",
        metavar="OUT",
        help="write the combined CSV to OUT ('-' for stdout). Default: stdout",
    )
    args = parser.parse_args(argv)

    if len(args.paths) < 1:
        print("csv-union: at least one CSV path is required", file=sys.stderr)
        return 2

    loaded = []
    for path in args.paths:
        try:
            headers, rows = read_csv(path)
        except OSError as exc:
            print(f"csv-union: {exc}", file=sys.stderr)
            return 2
        if not headers:
            print(f"csv-union: {path}: no header row", file=sys.stderr)
            return 2
        loaded.append((path, headers, rows))

    out_fields = union_headers([headers for _path, headers, _rows in loaded])
    if args.source_col:
        if args.source_col in out_fields:
            print(
                f"csv-union: --source-col {args.source_col!r} already exists in the input",
                file=sys.stderr,
            )
            return 2
        out_fields = out_fields + [args.source_col]

    files_report = []
    all_rows = []
    schema_differ = False
    first_headers = loaded[0][1]
    for path, headers, rows in loaded:
        info = describe_file(path, headers, rows, [n for n in out_fields if n != args.source_col])
        files_report.append(info)
        if headers != first_headers:
            schema_differ = True
        aligned = align_rows(rows, headers, [n for n in out_fields if n != args.source_col])
        if args.source_col:
            for row in aligned:
                row[args.source_col] = path
        all_rows.extend(aligned)

    if args.strict and schema_differ:
        report = {
            "files": files_report,
            "output_columns": out_fields,
            "output_rows": len(all_rows),
            "ok": False,
            "failed_checks": ["column names differ across files (--strict)"],
        }
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 1

    dest = args.write if args.write is not None else "-"
    try:
        if dest == "-":
            writer = csv.DictWriter(sys.stdout, fieldnames=out_fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(all_rows)
        else:
            with open(dest, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=out_fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(all_rows)
    except OSError as exc:
        print(f"csv-union: {exc}", file=sys.stderr)
        return 2

    report = {
        "files": files_report,
        "output_columns": out_fields,
        "output_rows": len(all_rows),
        "written": dest,
        "ok": True,
    }
    print(json.dumps(report, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

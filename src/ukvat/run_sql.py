"""Runs .sql files with DuckDB, from the repo root: python -m ukvat.run_sql sql/sample.sql"""

import sys

import duckdb


def run(path):
    con = duckdb.connect()
    with open(path, encoding="utf-8") as f:
        res = con.execute(f.read())
    # only the last statement's rows come back, so numbers.sql ends with a select
    if res.description:
        cols = [d[0] for d in res.description]
        for row in res.fetchall():
            print(dict(zip(cols, row, strict=True)))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        run(p)
        print(f"ran {p}")

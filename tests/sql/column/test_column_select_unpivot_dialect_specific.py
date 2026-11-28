import pytest

from sqllineage.utils.entities import ColumnQualifierTuple

from ...helpers import assert_column_lineage_equal

# the value column and the name column created by UNPIVOT are read from the columns in
# the IN list: the value column holds their values, the name column their names
_unpivot_dialects = [
    "bigquery",
    "databricks",
    "duckdb",
    "oracle",
    "redshift",
    "snowflake",
    "sparksql",
    "tsql",
]


def _unpivot_lineage(target: str = "tab1") -> list:
    return [
        (ColumnQualifierTuple("id", "tab2"), ColumnQualifierTuple("id", target)),
        (ColumnQualifierTuple("q1", "tab2"), ColumnQualifierTuple("quarter", target)),
        (ColumnQualifierTuple("q2", "tab2"), ColumnQualifierTuple("quarter", target)),
        (ColumnQualifierTuple("q1", "tab2"), ColumnQualifierTuple("sales", target)),
        (ColumnQualifierTuple("q2", "tab2"), ColumnQualifierTuple("sales", target)),
    ]


# tsql requires an alias for UNPIVOT
@pytest.mark.parametrize("dialect", [d for d in _unpivot_dialects if d != "tsql"])
def test_select_column_from_unpivot(dialect: str):
    sql = """INSERT INTO tab1
SELECT id, quarter, sales
FROM tab2 UNPIVOT (sales FOR quarter IN (q1, q2))"""
    assert_column_lineage_equal(
        sql, _unpivot_lineage(), dialect=dialect, test_sqlparse=False
    )


@pytest.mark.parametrize("dialect", _unpivot_dialects)
def test_select_column_from_unpivot_with_alias_unqualified(dialect: str):
    sql = """INSERT INTO tab1
SELECT id, quarter, sales
FROM tab2 UNPIVOT (sales FOR quarter IN (q1, q2)) AS u"""
    assert_column_lineage_equal(
        sql, _unpivot_lineage(), dialect=dialect, test_sqlparse=False
    )


@pytest.mark.parametrize("dialect", _unpivot_dialects)
def test_select_column_from_subquery_unpivot(dialect: str):
    sql = """INSERT INTO tab1
SELECT u.id, u.quarter, u.sales
FROM (SELECT id, q1, q2 FROM tab2) AS sq UNPIVOT (sales FOR quarter IN (q1, q2)) AS u"""
    assert_column_lineage_equal(
        sql, _unpivot_lineage(), dialect=dialect, test_sqlparse=False
    )


@pytest.mark.parametrize("dialect", ["snowflake", "databricks", "sparksql"])
def test_select_column_from_unpivot_include_nulls_in_expression(dialect: str):
    sql = """INSERT INTO tab1
SELECT id, sum(sales) AS total
FROM tab2 UNPIVOT INCLUDE NULLS (sales FOR quarter IN (q1, q2))
GROUP BY id"""
    assert_column_lineage_equal(
        sql,
        [
            (ColumnQualifierTuple("id", "tab2"), ColumnQualifierTuple("id", "tab1")),
            (
                ColumnQualifierTuple("q1", "tab2"),
                ColumnQualifierTuple("total", "tab1"),
            ),
            (
                ColumnQualifierTuple("q2", "tab2"),
                ColumnQualifierTuple("total", "tab1"),
            ),
        ],
        dialect=dialect,
        test_sqlparse=False,
    )


@pytest.mark.parametrize("dialect", ["databricks", "duckdb", "sparksql"])
def test_select_column_from_unpivot_multiple_value_columns(dialect: str):
    sql = """INSERT INTO tab1
SELECT id, half, first_quarter, second_quarter
FROM tab2 UNPIVOT (
    (first_quarter, second_quarter) FOR half IN ((q1, q2) AS h1, (q3, q4) AS h2)
)"""
    assert_column_lineage_equal(
        sql,
        [
            (ColumnQualifierTuple("id", "tab2"), ColumnQualifierTuple("id", "tab1")),
            (
                ColumnQualifierTuple("q1", "tab2"),
                ColumnQualifierTuple("first_quarter", "tab1"),
            ),
            (
                ColumnQualifierTuple("q3", "tab2"),
                ColumnQualifierTuple("first_quarter", "tab1"),
            ),
            (
                ColumnQualifierTuple("q2", "tab2"),
                ColumnQualifierTuple("second_quarter", "tab1"),
            ),
            (
                ColumnQualifierTuple("q4", "tab2"),
                ColumnQualifierTuple("second_quarter", "tab1"),
            ),
        ]
        + [
            (ColumnQualifierTuple(q, "tab2"), ColumnQualifierTuple("half", "tab1"))
            for q in ["q1", "q2", "q3", "q4"]
        ],
        dialect=dialect,
        test_sqlparse=False,
    )


@pytest.mark.parametrize("dialect", ["snowflake", "tsql"])
def test_select_column_from_unpivot_in_union(dialect: str):
    sql = """INSERT INTO tab1
SELECT id, sales FROM tab3
UNION ALL
SELECT id, sales FROM tab2 UNPIVOT (sales FOR quarter IN (q1, q2)) AS u"""
    assert_column_lineage_equal(
        sql,
        [
            (ColumnQualifierTuple("id", "tab2"), ColumnQualifierTuple("id", "tab1")),
            (ColumnQualifierTuple("id", "tab3"), ColumnQualifierTuple("id", "tab1")),
            (
                ColumnQualifierTuple("sales", "tab3"),
                ColumnQualifierTuple("sales", "tab1"),
            ),
            (
                ColumnQualifierTuple("q1", "tab2"),
                ColumnQualifierTuple("sales", "tab1"),
            ),
            (
                ColumnQualifierTuple("q2", "tab2"),
                ColumnQualifierTuple("sales", "tab1"),
            ),
        ],
        dialect=dialect,
        test_sqlparse=False,
    )


def test_select_column_from_unpivot_joined_column_with_same_name():
    sql = """INSERT INTO tab1
SELECT u.id, u.sales, o.sales AS other_sales
FROM tab2 UNPIVOT (sales FOR quarter IN (q1, q2)) AS u
JOIN tab3 AS o ON u.id = o.id"""
    assert_column_lineage_equal(
        sql,
        [
            (ColumnQualifierTuple("id", "tab2"), ColumnQualifierTuple("id", "tab1")),
            (
                ColumnQualifierTuple("q1", "tab2"),
                ColumnQualifierTuple("sales", "tab1"),
            ),
            (
                ColumnQualifierTuple("q2", "tab2"),
                ColumnQualifierTuple("sales", "tab1"),
            ),
            (
                ColumnQualifierTuple("sales", "tab3"),
                ColumnQualifierTuple("other_sales", "tab1"),
            ),
        ],
        dialect="snowflake",
        test_sqlparse=False,
    )

import pytest

from app.utils.csv_parser import build_column_map, parse_csv


def test_build_column_map_recognizes_synonyms():
    header = ["Transaction Date", "Narration", "Debit", "Credit"]
    mapping = build_column_map(header)
    assert mapping["date"] == "Transaction Date"
    assert mapping["description"] == "Narration"
    assert mapping["debit"] == "Debit"
    assert mapping["credit"] == "Credit"


def test_parse_csv_amount_sign_inference():
    csv_bytes = b"date,description,amount\n2026-01-01,Refund,-200\n2026-01-02,Purchase,300\n"
    result = parse_csv(csv_bytes)
    assert len(result.rows) == 2
    assert result.rows[0].transaction_type == "debit"
    assert result.rows[0].amount == 200
    assert result.rows[1].transaction_type == "credit"
    assert result.rows[1].amount == 300


def test_parse_csv_explicit_type_column_overrides_sign():
    csv_bytes = (
        b"date,description,amount,type\n"
        b"2026-01-01,Purchase,438,debit\n"
        b"2026-01-02,Salary,65000,credit\n"
    )
    result = parse_csv(csv_bytes)
    assert result.rows[0].transaction_type == "debit"
    assert result.rows[1].transaction_type == "credit"


def test_parse_csv_debit_credit_columns():
    csv_bytes = (
        b"transaction_date,narration,debit,credit\n"
        b"2026-02-01,ELECTRICITY BILL,1500,\n"
        b"2026-02-02,SALARY CREDIT,,65000\n"
    )
    result = parse_csv(csv_bytes)
    assert len(result.rows) == 2
    assert result.rows[0].transaction_type == "debit"
    assert result.rows[0].amount == 1500
    assert result.rows[1].transaction_type == "credit"
    assert result.rows[1].amount == 65000


def test_parse_csv_missing_required_columns_raises():
    csv_bytes = b"foo,bar\n1,2\n"
    with pytest.raises(ValueError):
        parse_csv(csv_bytes)


def test_parse_csv_missing_amount_columns_raises():
    csv_bytes = b"date,description\n2026-01-01,Something\n"
    with pytest.raises(ValueError):
        parse_csv(csv_bytes)


def test_parse_csv_collects_row_errors_without_raising():
    csv_bytes = b"date,description,amount\nnot-a-date,X,100\n2026-01-01,Y,200\n"
    result = parse_csv(csv_bytes)
    assert len(result.rows) == 1
    assert len(result.errors) == 1
    assert result.errors[0].row == 2
    assert result.total_rows == 2


def test_parse_csv_zero_amount_is_row_error():
    csv_bytes = b"date,description,amount\n2026-01-01,Nothing,0\n"
    result = parse_csv(csv_bytes)
    assert len(result.rows) == 0
    assert len(result.errors) == 1


def test_parse_csv_merchant_and_reference_optional_columns():
    csv_bytes = (
        b"date,description,amount,merchant,reference\n"
        b"2026-01-01,SWIGGY ORDER 123,438,Swiggy,TXN001\n"
    )
    result = parse_csv(csv_bytes)
    assert result.rows[0].merchant == "Swiggy"
    assert result.rows[0].reference == "TXN001"

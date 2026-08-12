"""Flexible CSV -> canonical transaction field mapping.

Bank/payment-app exports use wildly different column names for the same
concept ("date" vs "transaction_date" vs "value_date"). This module
normalizes a header row to canonical field names and parses each row into
primitive values.

Row-level problems (bad date, unparseable amount, missing description) are
collected as errors rather than raised — one malformed row must never abort
the whole import (see master prompt Rule 26). A missing *required column*
(no recognizable date/description/amount at all) is a file-level problem and
does raise, since there's nothing sensible to parse.
"""

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import datetime

FIELD_SYNONYMS: dict[str, set[str]] = {
    "date": {"date", "transaction_date", "txn_date", "value_date", "posting_date"},
    "description": {"description", "narration", "particulars", "details", "remarks", "memo"},
    "merchant": {"merchant", "payee", "merchant_name"},
    "amount": {"amount", "txn_amount", "transaction_amount"},
    "debit": {"debit", "withdrawal", "dr", "debit_amount"},
    "credit": {"credit", "deposit", "cr", "credit_amount"},
    "type": {"type", "transaction_type", "dr_cr", "cr_dr"},
    "reference": {"reference", "ref_no", "reference_number", "transaction_id", "utr"},
    "currency": {"currency", "curr"},
}

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d-%b-%Y",
]


@dataclass
class ParsedRow:
    transaction_date: datetime
    description: str
    merchant: str | None
    amount: float
    transaction_type: str
    currency: str
    reference: str | None


@dataclass
class RowError:
    row: int
    message: str


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    total_rows: int = 0


def compute_file_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def build_column_map(header: list[str]) -> dict[str, str]:
    """Map canonical field name -> the actual CSV column name that matched it."""
    normalized = {h: h.strip().lower().replace(" ", "_") for h in header}
    column_map: dict[str, str] = {}
    for canonical, synonyms in FIELD_SYNONYMS.items():
        for original, norm in normalized.items():
            if norm in synonyms and canonical not in column_map:
                column_map[canonical] = original
                break
    return column_map


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_amount(value: str) -> float | None:
    cleaned = value.strip().replace(",", "").replace("₹", "").replace("$", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_csv(raw_bytes: bytes, default_currency: str = "INR") -> ParseResult:
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("The uploaded file has no header row.")

    column_map = build_column_map(list(reader.fieldnames))
    if "date" not in column_map or "description" not in column_map:
        raise ValueError(
            "Could not find required 'date' and 'description' columns. "
            f"Detected columns: {list(reader.fieldnames)}"
        )
    has_amount = "amount" in column_map
    has_debit_credit = "debit" in column_map or "credit" in column_map
    if not has_amount and not has_debit_credit:
        raise ValueError(
            "Could not find an 'amount' column, or 'debit'/'credit' columns. "
            f"Detected columns: {list(reader.fieldnames)}"
        )

    result = ParseResult()
    for row_num, raw_row in enumerate(reader, start=2):  # header is row 1
        result.total_rows += 1
        try:
            parsed = _parse_row(raw_row, column_map, default_currency)
            result.rows.append(parsed)
        except ValueError as exc:
            result.errors.append(RowError(row=row_num, message=str(exc)))

    return result


def _parse_row(
    raw_row: dict[str, str], column_map: dict[str, str], default_currency: str
) -> ParsedRow:
    date_raw = (raw_row.get(column_map["date"]) or "").strip()
    description_raw = (raw_row.get(column_map["description"]) or "").strip()

    if not date_raw:
        raise ValueError("Missing transaction date")
    if not description_raw:
        raise ValueError("Missing description")

    parsed_date = _parse_date(date_raw)
    if parsed_date is None:
        raise ValueError(f"Unrecognized date format: '{date_raw}'")

    transaction_type: str | None = None
    amount: float | None = None

    if "debit" in column_map or "credit" in column_map:
        debit_raw = raw_row.get(column_map.get("debit", ""), "") or ""
        credit_raw = raw_row.get(column_map.get("credit", ""), "") or ""
        debit_val = _parse_amount(debit_raw) or 0.0
        credit_val = _parse_amount(credit_raw) or 0.0
        if debit_val:
            amount, transaction_type = abs(debit_val), "debit"
        elif credit_val:
            amount, transaction_type = abs(credit_val), "credit"

    if amount is None and "amount" in column_map:
        amount_raw = raw_row.get(column_map["amount"], "") or ""
        parsed_amount = _parse_amount(amount_raw)
        if parsed_amount is None:
            raise ValueError(f"Unrecognized amount value: '{amount_raw}'")
        if "type" in column_map:
            type_raw = (raw_row.get(column_map["type"]) or "").strip().lower()
            transaction_type = "credit" if type_raw in {"credit", "cr", "c"} else "debit"
        else:
            transaction_type = "credit" if parsed_amount > 0 else "debit"
        amount = abs(parsed_amount)

    if amount is None or transaction_type is None:
        raise ValueError("Could not determine a valid amount and transaction type for this row")
    if amount == 0:
        raise ValueError("Transaction amount is zero")

    merchant = None
    if "merchant" in column_map:
        merchant = (raw_row.get(column_map["merchant"]) or "").strip() or None

    reference = None
    if "reference" in column_map:
        reference = (raw_row.get(column_map["reference"]) or "").strip() or None

    currency = default_currency
    if "currency" in column_map:
        currency = (raw_row.get(column_map["currency"]) or "").strip() or default_currency

    return ParsedRow(
        transaction_date=parsed_date,
        description=description_raw,
        merchant=merchant,
        amount=amount,
        transaction_type=transaction_type,
        currency=currency,
        reference=reference,
    )

"""Tests for the normalization module."""

from datetime import datetime

from collector.core.schemas import OpportunityStatus, RawRecord
from collector.ml.normalizer import (
    infer_status,
    normalize_vendor_name,
    parse_currency,
    parse_date,
    raw_to_canonical,
)


class TestNormalizeVendorName:
    def test_strips_suffix(self):
        assert normalize_vendor_name("Acme Corp.") == "acme"

    def test_strips_llc(self):
        assert normalize_vendor_name("Big Data LLC") == "big data"

    def test_none_input(self):
        assert normalize_vendor_name(None) is None

    def test_empty_string(self):
        assert normalize_vendor_name("") is None


class TestParseDate:
    def test_iso_format(self):
        assert parse_date("2024-03-15") == datetime(2024, 3, 15)

    def test_us_format(self):
        assert parse_date("03/15/2024") == datetime(2024, 3, 15)

    def test_long_format(self):
        assert parse_date("March 15, 2024") == datetime(2024, 3, 15)

    def test_none(self):
        assert parse_date(None) is None

    def test_garbage(self):
        assert parse_date("not a date") is None


class TestParseCurrency:
    def test_dollar_amount(self):
        amount, cur = parse_currency("$1,234.56")
        assert amount == 1234.56
        assert cur == "USD"

    def test_none(self):
        amount, cur = parse_currency(None)
        assert amount is None

    def test_garbage(self):
        amount, cur = parse_currency("TBD")
        assert amount is None


class TestInferStatus:
    def test_open(self):
        assert infer_status({"status": "Active"}) == OpportunityStatus.OPEN

    def test_closed(self):
        assert infer_status({"note": "This opportunity is closed"}) == OpportunityStatus.CLOSED

    def test_awarded(self):
        assert infer_status({"status": "Awarded"}) == OpportunityStatus.AWARDED

    def test_unknown(self):
        assert infer_status({"title": "Something"}) == OpportunityStatus.UNKNOWN


class TestRawToCanonical:
    def test_basic_conversion(self):
        raw = RawRecord(
            source_id="ABC-1",
            source_name="test",
            source_url="https://example.com/ABC-1",
            extracted={
                "title": "Build New Library",
                "agency": "Dept of Education",
                "posted_date": "2024-01-10",
                "due_date": "2024-02-10",
            },
        )
        canon = raw_to_canonical(raw)
        assert canon.title == "Build New Library"
        assert canon.agency == "Dept of Education"
        assert canon.posted_date == datetime(2024, 1, 10)
        assert canon.due_date == datetime(2024, 2, 10)
        assert canon.record_id != ""

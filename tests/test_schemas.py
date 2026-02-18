"""Tests for core Pydantic schemas."""

from collector.core.schemas import (
    CanonicalRecord,
    OpportunityCategory,
    OpportunityStatus,
    RawRecord,
)


class TestRawRecord:
    def test_content_hash_computed(self):
        rec = RawRecord(
            source_id="123",
            source_name="test_source",
            source_url="https://example.com/123",
            extracted={"title": "Test Opportunity", "agency": "Test Agency"},
        )
        assert rec.content_hash != ""
        assert len(rec.content_hash) == 64  # SHA-256

    def test_same_data_same_hash(self):
        kwargs = dict(
            source_id="123",
            source_name="test_source",
            source_url="https://example.com/123",
            extracted={"title": "Test", "agency": "Agency"},
        )
        r1 = RawRecord(**kwargs)
        r2 = RawRecord(**kwargs)
        assert r1.content_hash == r2.content_hash

    def test_different_data_different_hash(self):
        base = dict(source_id="123", source_name="src", source_url="https://example.com")
        r1 = RawRecord(**base, extracted={"title": "A"})
        r2 = RawRecord(**base, extracted={"title": "B"})
        assert r1.content_hash != r2.content_hash


class TestCanonicalRecord:
    def test_record_id_computed(self):
        rec = CanonicalRecord(
            record_id="",
            source_name="test",
            source_id="456",
            source_url="https://example.com/456",
            title="Build a Bridge",
        )
        assert rec.record_id != ""
        assert len(rec.record_id) == 64

    def test_defaults(self):
        rec = CanonicalRecord(
            record_id="",
            source_name="test",
            source_id="789",
            source_url="https://example.com/789",
            title="Supply Office Chairs",
        )
        assert rec.status == OpportunityStatus.UNKNOWN
        assert rec.category == OpportunityCategory.OTHER
        assert rec.version == 1
        assert rec.currency == "USD"

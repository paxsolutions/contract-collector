"""Tests for duplicate detection."""

from collector.ml.dedup import find_duplicates


class TestFindDuplicates:
    def test_identical_records(self):
        records = [
            {"title": "Road repair on Highway 101", "description": "Full road repair project"},
            {"title": "Road repair on Highway 101", "description": "Full road repair project"},
        ]
        dupes = find_duplicates(records, threshold=0.85)
        assert len(dupes) == 1
        assert dupes[0][2] >= 0.85

    def test_different_records(self):
        records = [
            {"title": "Road repair on Highway 101", "description": "Asphalt paving"},
            {"title": "IT cloud migration project", "description": "Migrate to AWS"},
        ]
        dupes = find_duplicates(records, threshold=0.85)
        assert len(dupes) == 0

    def test_empty_list(self):
        assert find_duplicates([], threshold=0.85) == []

    def test_single_record(self):
        assert find_duplicates([{"title": "solo"}], threshold=0.85) == []

"""Tests for the category classifier."""

from collector.core.schemas import OpportunityCategory
from collector.ml.classifier import CategoryClassifier


class TestCategoryClassifier:
    def setup_method(self):
        self.clf = CategoryClassifier()
        self.clf.train()  # train from seed data

    def test_construction(self):
        cat, conf = self.clf.predict("highway bridge construction paving")
        assert cat == OpportunityCategory.CONSTRUCTION
        assert conf > 0.3

    def test_it_services(self):
        cat, conf = self.clf.predict("cloud migration cybersecurity software")
        assert cat == OpportunityCategory.IT_SERVICES
        assert conf > 0.3

    def test_batch_predict(self):
        results = self.clf.predict_batch(["building renovation", "office supplies purchase"])
        assert len(results) == 2
        assert all(isinstance(r[0], OpportunityCategory) for r in results)

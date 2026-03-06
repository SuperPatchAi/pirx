import pytest
from app.ml.learning_module import LearningModule, Insight


def make_features_history(n: int = 8, **overrides):
    history = []
    for i in range(n):
        base = {
            "rolling_distance_7d": 30000 + i * 1000,
            "rolling_distance_21d": 85000 + i * 3000,
            "z4_pct": 0.12,
            "z5_pct": 0.05,
            "weekly_load_stddev": 4000,
            "acwr_4w": 1.1,
        }
        base.update(overrides)
        history.append(base)
    return history


class TestConsistencyPatterns:
    def test_detects_consistent_training(self):
        history = make_features_history(8, weekly_load_stddev=2500)
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Consistent" in t for t in titles)

    def test_detects_variable_training(self):
        history = make_features_history(4, weekly_load_stddev=3000)
        history[-1]["weekly_load_stddev"] = 8000
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Variability" in t for t in titles)


class TestVolumeTrends:
    def test_detects_volume_increase(self):
        history = make_features_history(6)
        for i, h in enumerate(history):
            h["rolling_distance_21d"] = 70000 + i * 8000
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Volume Building" in t for t in titles)

    def test_detects_volume_decrease(self):
        history = make_features_history(6)
        for i, h in enumerate(history):
            h["rolling_distance_21d"] = 120000 - i * 8000
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Volume Reduction" in t for t in titles)


class TestIntensityPatterns:
    def test_detects_high_threshold(self):
        history = make_features_history(6, z4_pct=0.18)
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Threshold" in t for t in titles)

    def test_detects_low_threshold(self):
        history = make_features_history(6, z4_pct=0.03)
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Threshold" in t.lower() or "Low" in t for t in titles)


class TestRiskPatterns:
    def test_detects_high_acwr(self):
        history = make_features_history(4, acwr_4w=1.6)
        insights = LearningModule.analyze_training_patterns(history)
        titles = [i.title for i in insights]
        assert any("Elevated" in t for t in titles)

    def test_no_risk_normal_acwr(self):
        history = make_features_history(4, acwr_4w=1.0)
        insights = LearningModule.analyze_training_patterns(history)
        risk_insights = [i for i in insights if i.category == "risk"]
        assert len(risk_insights) == 0


class TestSummaryGeneration:
    def test_generates_three_sections(self):
        insights = [
            Insight("consistency", "Title1", "Body1", "supported", 0.9, 10),
            Insight("trend", "Title2", "Body2", "emerging", 0.7, 5),
            Insight("risk", "Title3", "Body3", "observational", 0.5, 3),
        ]
        summary = LearningModule.generate_summary(insights)
        assert "what_today_supports" in summary
        assert "what_is_defensible" in summary
        assert "what_needs_development" in summary
        assert len(summary["what_today_supports"]) == 1
        assert len(summary["what_is_defensible"]) == 1
        assert len(summary["what_needs_development"]) == 1

    def test_empty_insights(self):
        summary = LearningModule.generate_summary([])
        assert len(summary["what_today_supports"]) == 0

    def test_insufficient_data(self):
        insights = LearningModule.analyze_training_patterns([])
        assert len(insights) == 0

    def test_single_data_point(self):
        insights = LearningModule.analyze_training_patterns([{"weekly_load_stddev": 3000}])
        assert len(insights) == 0

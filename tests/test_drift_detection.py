from netsentinel.services.drift_detection import DriftDetectionService
from netsentinel.services.feature_engineering import FeatureEngineeringService
from netsentinel.services.sample_data import generate_synthetic_network_flows


def test_drift_detection_reports_feature_scores() -> None:
    feature_engineer = FeatureEngineeringService()
    reference = feature_engineer.build_features(generate_synthetic_network_flows(300, seed=4)).features
    current = feature_engineer.build_features(generate_synthetic_network_flows(300, seed=5, drift=True)).features

    report = DriftDetectionService(threshold=0.2).detect(reference, current)

    assert report.features
    assert report.drift_score >= 0
    assert report.features[0].feature

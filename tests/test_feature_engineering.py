import pandas as pd

from netsentinel.services.feature_engineering import FEATURE_COLUMNS, FeatureEngineeringService
from netsentinel.services.sample_data import generate_synthetic_network_flows


def test_build_features_from_demo_data() -> None:
    df = generate_synthetic_network_flows(n_rows=50, seed=3)
    result = FeatureEngineeringService().build_features(df)

    assert list(result.features.columns) == FEATURE_COLUMNS
    assert result.features.shape == (50, len(FEATURE_COLUMNS))
    assert result.labels is not None
    assert set(result.labels.unique()).issubset({0, 1})


def test_build_features_from_cicids_style_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "Flow Duration": 100000,
                "Protocol": "TCP",
                "Source Port": 49152,
                "Destination Port": 443,
                "Total Fwd Packets": 10,
                "Total Backward Packets": 8,
                "Total Length of Fwd Packets": 1800,
                "Total Length of Bwd Packets": 2400,
                "Flow Bytes/s": 42000,
                "Flow Packets/s": 180,
                "Packet Length Mean": 210,
                "Packet Length Std": 30,
                "Label": "BENIGN",
            }
        ]
    )

    result = FeatureEngineeringService().build_features(df)

    assert result.features.loc[0, "dst_port"] == 443
    assert result.features.loc[0, "protocol_code"] == 6
    assert result.labels is not None
    assert result.labels.iloc[0] == 0

from netsentinel.services.data_validation import DataValidationService
from netsentinel.services.sample_data import generate_synthetic_network_flows


def test_valid_sample_data_scores_high() -> None:
    df = generate_synthetic_network_flows(n_rows=120, seed=1)
    result = DataValidationService().validate_schema(df)

    assert result.is_valid
    assert result.quality_score >= 80
    assert result.errors == []


def test_invalid_port_is_rejected() -> None:
    df = generate_synthetic_network_flows(n_rows=10, seed=2)
    df.loc[0, "dst_port"] = 70000

    result = DataValidationService().validate_schema(df)

    assert not result.is_valid
    assert any("dst_port" in error for error in result.errors)

from netsentinel.services.model_registry import ModelRegistry
from netsentinel.services.model_training import ModelTrainingService
from netsentinel.services.sample_data import generate_synthetic_network_flows


def test_training_registers_best_model(tmp_path) -> None:
    df = generate_synthetic_network_flows(n_rows=350, seed=6)
    registry = ModelRegistry(tmp_path / "registry")

    result = ModelTrainingService().train_all(
        df,
        registry=registry,
        reference_data_path=tmp_path / "reference_features.csv",
    )

    active = registry.get_active_record()
    model = registry.load_model()

    assert active is not None
    assert active.model_id == result.best_model.model_id
    assert active.metrics["f1"] >= 0.8
    assert hasattr(model, "predict")
    assert (tmp_path / "reference_features.csv").exists()

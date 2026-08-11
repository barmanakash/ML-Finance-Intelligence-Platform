from pathlib import Path
from pydantic import BaseModel

class MLConfig(BaseModel):
    # Paths
    project_root: Path = Path(__file__).parent.parent.parent
    models_dir: Path = project_root / "models"
    data_dir: Path = project_root / "data"
    sample_data_dir: Path = data_dir / "sample"
    
    # Training
    random_seed: int = 42
    test_size: float = 0.2
    validation_size: float = 0.1
    
    # Categorization
    categorization_model_name: str = "transaction-classifier"
    tfidf_max_features: int = 5000
    tfidf_ngram_range: tuple[int, int] = (1, 2)
    
    # Anomaly Detection  
    anomaly_model_name: str = "anomaly-detector"
    anomaly_contamination: float = 0.05
    anomaly_n_estimators: int = 200
    
    # Forecasting
    forecast_model_name: str = "expense-forecaster"
    forecast_horizons: list[int] = [7, 30, 90]
    
    # MLflow
    mlflow_experiment_categorization: str = "transaction-categorization"
    mlflow_experiment_anomaly: str = "anomaly-detection"
    mlflow_experiment_forecasting: str = "expense-forecasting"

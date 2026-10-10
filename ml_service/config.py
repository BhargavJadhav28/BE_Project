"""
Microgrid Configuration and Asset Sizing.

Centralized immutable dataclass managing asset ratings, temporal parameters,
model hyperparameters, quality targets, and artifact paths.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class MicrogridConfig:
    """Configuration parameters for the 24-hour microgrid forecasting subsystem."""

    # Asset Electrical Ratings
    pv_peak_kw: float = 50.0        # Rated Solar PV inverter capacity (kW)
    load_peak_kw: float = 45.0      # Rated peak load capacity (kW)
    base_load_kw: float = 10.0      # Minimum overnight baseload (kW)
    load_transient_peak_kw: float = 54.0  # Transient load peak ceiling (1.2 * load_peak_kw)

    # Temporal & Horizon Parameters
    forecast_horizon_hours: int = 24
    lookback_window_hours: int = 48  # Minimum contiguous telemetry history required
    max_imputable_gap_hours: int = 3 # Maximum consecutive sensor dropout permitted

    # Data Ingestion Source
    telemetry_source_type: Literal["synthetic", "csv"] = "csv"
    csv_telemetry_path: str = "data/raw_telemetry.csv"
    random_seed: int = 42

    # Model Hyperparameter Budget (Tuned for Laptop CPU)
    n_estimators: int = 150
    learning_rate: float = 0.05
    num_leaves: int = 31
    max_depth: int = 6
    early_stopping_rounds: int = 15
    n_jobs: int = -1

    # Quality Acceptance Targets
    pv_daylight_nmae_target: float = 0.05   # <= 5.0% of PV peak
    load_nmae_target: float = 0.06          # <= 6.0% of Load peak
    r2_score_target: float = 0.85

    # Artifact Paths
    artifacts_dir: str = "artifacts"
    pv_model_filename: str = "pv_model.joblib"
    load_model_filename: str = "load_model.joblib"
    manifest_filename: str = "manifest.json"

    def get_artifacts_dir_path(self, base_dir: Path | str | None = None) -> Path:
        """Resolve the artifacts directory path."""
        path = Path(self.artifacts_dir)
        if path.is_absolute():
            return path
        if base_dir is not None:
            return Path(base_dir) / path
        # Default to directory containing the package or current working directory
        module_dir = Path(__file__).resolve().parent
        return module_dir / path

    def get_pv_model_path(self, base_dir: Path | str | None = None) -> Path:
        return self.get_artifacts_dir_path(base_dir) / self.pv_model_filename

    def get_load_model_path(self, base_dir: Path | str | None = None) -> Path:
        return self.get_artifacts_dir_path(base_dir) / self.load_model_filename

    def get_manifest_path(self, base_dir: Path | str | None = None) -> Path:
        return self.get_artifacts_dir_path(base_dir) / self.manifest_filename

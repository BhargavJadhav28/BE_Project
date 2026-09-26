"""
End-to-End Pipeline Integration Test.

Executes train/eval cycle, artifact creation, 24-step forecast execution,
and verifies output shape = 24, non-negative bounds, nocturnal solar zeroing,
and inference latency < 50ms.
"""

from pathlib import Path
import tempfile
import time

import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig
from ml_service.data.synthetic_generator import generate_synthetic_telemetry
from ml_service.features.pipeline import build_training_dataset
from ml_service.models.load_model import LoadForecaster
from ml_service.models.pv_model import PVForecaster
from ml_service.predict import MicrogridForecaster


def test_end_to_end_pipeline_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = MicrogridConfig(
            artifacts_dir=str(tmp_path),
            n_estimators=50, # Fast training for test
            lookback_window_hours=48,
            forecast_horizon_hours=24,
        )

        # 1. 60-Day Telemetry (1440 hours)
        telemetry_df = generate_synthetic_telemetry(config, hours=1440)
        assert len(telemetry_df) == 1440

        # 2. Build Dataset & Train
        X, y_pv, y_load = build_training_dataset(telemetry_df, config)
        assert len(X) == (1440 - 48 - 24) * 24

        pv_model = PVForecaster(config).fit(X, y_pv)
        load_model = LoadForecaster(config).fit(X, y_load)

        # Save artifacts to temp dir
        pv_path = config.get_pv_model_path(base_dir=tmp_path)
        load_path = config.get_load_model_path(base_dir=tmp_path)
        pv_model.save(pv_path)
        load_model.save(load_path)

        # 3. Instantiate MicrogridForecaster pointing to temp artifacts
        forecaster = MicrogridForecaster(config, artifacts_dir=tmp_path)

        # 4. Generate 24h prediction for an origin near the end of the series
        origin = pd.Timestamp("2026-02-20 18:00:00") # Evening origin
        hist_start = origin - pd.Timedelta(hours=48)
        future_start = origin + pd.Timedelta(hours=1)
        future_end = origin + pd.Timedelta(hours=24)

        history_df = telemetry_df[(telemetry_df["timestamp"] >= hist_start) & (telemetry_df["timestamp"] <= origin)].copy()
        weather_df = telemetry_df[(telemetry_df["timestamp"] >= future_start) & (telemetry_df["timestamp"] <= future_end)][
            ["timestamp", "ghi", "temp_amb", "cloud_cover"]
        ].copy()

        # Measure latency
        t0 = time.perf_counter()
        result = forecaster.predict_next_24h(origin, history_df, weather_df)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # 5. Assertions
        # Shape = 24
        assert len(result["timestamps"]) == 24
        assert len(result["p_pv_forecast"]) == 24
        assert len(result["p_load_forecast"]) == 24

        # Non-negative bounds & physical limits
        pv_preds = np.array(result["p_pv_forecast"])
        load_preds = np.array(result["p_load_forecast"])

        assert (pv_preds >= 0.0).all()
        assert (pv_preds <= config.pv_peak_kw).all()
        assert (load_preds >= 0.0).all()
        assert (load_preds <= 1.2 * config.load_peak_kw).all()

        # Zero nocturnal solar
        weather_ghi = weather_df["ghi"].to_numpy()
        night_indices = np.where(weather_ghi <= 0.0)[0]
        assert len(night_indices) > 0, "Test slice must contain nighttime hours"
        assert (pv_preds[night_indices] == 0.0).all(), "Nocturnal solar PV must be strictly 0.0 kW"

        # Inference latency < 50ms
        print(f"End-to-end inference latency: {latency_ms:.2f}ms")
        assert latency_ms < 50.0, f"Inference took {latency_ms:.2f}ms, exceeding 50ms SLA"

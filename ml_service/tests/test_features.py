"""
Unit tests for Feature Pipeline and Leakage Prevention.
"""

import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig
from ml_service.data.synthetic_generator import generate_synthetic_telemetry
from ml_service.features.pipeline import (
    LOAD_FEATURE_NAMES,
    PV_FEATURE_NAMES,
    FeaturePipeline,
    build_training_dataset,
)


def test_feature_pipeline_no_future_leakage():
    config = MicrogridConfig()
    pipeline = FeaturePipeline(config)

    telemetry = generate_synthetic_telemetry(config)
    origin = pd.Timestamp("2026-05-01 12:00:00")

    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    # Weather forecast for next 24h
    future_start = origin + pd.Timedelta(hours=1)
    future_end = origin + pd.Timedelta(hours=24)
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    feat_baseline = pipeline.extract_features_for_origin(origin, history_df, weather_df)

    # Now simulate future telemetry where future actual p_pv and p_load are altered
    # This should have ZERO impact on features extracted at origin T
    corrupted_telemetry = telemetry.copy()
    corrupted_mask = (corrupted_telemetry["timestamp"] >= future_start) & (corrupted_telemetry["timestamp"] <= future_end)
    corrupted_telemetry.loc[corrupted_mask, "p_pv"] = 99999.0
    corrupted_telemetry.loc[corrupted_mask, "p_load"] = 99999.0

    feat_corrupted = pipeline.extract_features_for_origin(origin, history_df, weather_df)

    # Features must match exactly
    for col in PV_FEATURE_NAMES + LOAD_FEATURE_NAMES:
        assert np.allclose(feat_baseline[col], feat_corrupted[col]), f"Feature leakage detected in {col}"


def test_cyclical_and_horizon_encodings():
    config = MicrogridConfig()
    pipeline = FeaturePipeline(config)
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-07-04 10:00:00") # Saturday
    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    future_start = origin + pd.Timedelta(hours=1)
    future_end = origin + pd.Timedelta(hours=24)
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    feat = pipeline.extract_features_for_origin(origin, history_df, weather_df)

    # 1. Horizon is strictly 1..24
    assert list(feat["horizon"]) == list(range(1, 25))

    # 2. Sin / Cos encodings are within [-1, 1]
    assert (feat["sin_hour"] >= -1.0).all() and (feat["sin_hour"] <= 1.0).all()
    assert (feat["cos_hour"] >= -1.0).all() and (feat["cos_hour"] <= 1.0).all()
    assert (feat["sin_day_of_year"] >= -1.0).all() and (feat["sin_day_of_year"] <= 1.0).all()
    assert (feat["cos_day_of_year"] >= -1.0).all() and (feat["cos_day_of_year"] <= 1.0).all()

    # 3. is_weekend indicator is binary
    assert set(feat["is_weekend"].unique()).issubset({0.0, 1.0})


def test_build_training_dataset_vectorization():
    config = MicrogridConfig()
    # Test on a short slice of 200 hours
    telemetry = generate_synthetic_telemetry(config, hours=200)

    X, y_pv, y_load = build_training_dataset(telemetry, config)

    expected_origins = 200 - config.lookback_window_hours - config.forecast_horizon_hours
    expected_rows = expected_origins * config.forecast_horizon_hours

    assert len(X) == expected_rows
    assert len(y_pv) == expected_rows
    assert len(y_load) == expected_rows

    for col in PV_FEATURE_NAMES:
        assert col in X.columns
    for col in LOAD_FEATURE_NAMES:
        assert col in X.columns

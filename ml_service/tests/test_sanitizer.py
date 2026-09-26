"""
Unit tests for Self-Healing Telemetry Sanitizer.
"""

import numpy as np
import pandas as pd
import pytest

from ml_service.config import MicrogridConfig
from ml_service.data.synthetic_generator import generate_synthetic_telemetry
from ml_service.features.sanitizer import TelemetryGapError, TelemetrySanitizer


def test_sanitizer_clean_input():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-04-10 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    clean_df = sanitizer.sanitize(history_df, origin=origin)
    assert len(clean_df) == 49
    assert clean_df["timestamp"].iloc[0] == hist_start
    assert clean_df["timestamp"].iloc[-1] == origin
    assert not clean_df.isna().any().any()


def test_sanitizer_recovers_2_hour_dropout():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-04-10 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    # Drop 2 consecutive rows in the middle (e.g. 10 hours before origin)
    drop_times = [origin - pd.Timedelta(hours=10), origin - pd.Timedelta(hours=9)]
    history_with_gap = history_df[~history_df["timestamp"].isin(drop_times)].copy()

    assert len(history_with_gap) == 47

    sanitized = sanitizer.sanitize(history_with_gap, origin=origin)
    assert len(sanitized) == 49
    assert not sanitized.isna().any().any()

    # Assert values at dropped timestamps were imputed linearly
    imputed_rows = sanitized[sanitized["timestamp"].isin(drop_times)]
    assert len(imputed_rows) == 2
    for col in ["p_pv", "p_load", "temp_amb", "cloud_cover", "ghi"]:
        assert not imputed_rows[col].isna().any()


def test_sanitizer_fails_on_4_hour_dropout():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-04-10 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    # Drop 4 consecutive rows (exceeds max_imputable_gap_hours=3)
    drop_times = [
        origin - pd.Timedelta(hours=12),
        origin - pd.Timedelta(hours=11),
        origin - pd.Timedelta(hours=10),
        origin - pd.Timedelta(hours=9),
    ]
    history_with_large_gap = history_df[~history_df["timestamp"].isin(drop_times)].copy()

    with pytest.raises(TelemetryGapError, match="Consecutive sensor dropout"):
        sanitizer.sanitize(history_with_large_gap, origin=origin)


def test_sanitizer_nocturnal_pv_zero_fill():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-04-10 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    # Find a nocturnal hour where ghi == 0 and drop p_pv (make it NaN)
    night_time = origin - pd.Timedelta(hours=10) # 02:00 AM
    history_df.loc[history_df["timestamp"] == night_time, "p_pv"] = np.nan
    history_df.loc[history_df["timestamp"] == night_time, "ghi"] = 0.0

    sanitized = sanitizer.sanitize(history_df, origin=origin)
    night_val = sanitized.loc[sanitized["timestamp"] == night_time, "p_pv"].values[0]
    assert night_val == 0.0


def test_sanitizer_tz_aware_origin_and_timestamps():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    origin_utc = pd.Timestamp("2026-04-10 12:00:00+00:00")
    hist_start = origin_utc - pd.Timedelta(hours=48)

    # Convert telemetry timestamps to UTC timezone-aware
    telemetry_tz = telemetry.copy()
    telemetry_tz["timestamp"] = telemetry_tz["timestamp"].dt.tz_localize("UTC")
    history_df = telemetry_tz[(telemetry_tz["timestamp"] >= hist_start) & (telemetry_tz["timestamp"] <= origin_utc)].copy()

    sanitized = sanitizer.sanitize(history_df, origin=origin_utc)
    assert len(sanitized) == 49
    # Ensure returned index/timestamps are normalized to timezone-naive UTC
    assert sanitized["timestamp"].dt.tz is None
    assert sanitized["timestamp"].iloc[-1] == pd.Timestamp("2026-04-10 12:00:00")
    assert not sanitized.isna().any().any()


def test_sanitizer_off_hour_origin_snapping():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    # Origin with off-hour minutes and seconds
    off_hour_origin = pd.Timestamp("2026-04-10 12:35:42")
    snapped_origin = pd.Timestamp("2026-04-10 12:00:00")
    hist_start = snapped_origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= snapped_origin)].copy()

    sanitized = sanitizer.sanitize(history_df, origin=off_hour_origin)
    assert len(sanitized) == 49
    assert sanitized["timestamp"].iloc[-1] == snapped_origin
    assert sanitized["timestamp"].iloc[0] == hist_start


def test_sanitizer_sensor_calibration_drift_clipping():
    config = MicrogridConfig()
    sanitizer = TelemetrySanitizer(lookback_window_hours=48, max_imputable_gap_hours=3)
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-04-10 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()

    # Inject negative nocturnal sensor drift (e.g. pyranometer zero-point offset)
    history_df.loc[history_df["timestamp"] == origin, "ghi"] = -3.5
    history_df.loc[history_df["timestamp"] == origin, "p_pv"] = -0.4
    history_df.loc[history_df["timestamp"] == origin, "p_load"] = -0.1

    sanitized = sanitizer.sanitize(history_df, origin=origin)
    assert (sanitized["ghi"] >= 0.0).all()
    assert (sanitized["p_pv"] >= 0.0).all()
    assert (sanitized["p_load"] >= 0.0).all()
    assert sanitized.loc[sanitized["timestamp"] == origin, "ghi"].iloc[0] == 0.0
    assert sanitized.loc[sanitized["timestamp"] == origin, "p_pv"].iloc[0] == 0.0
    assert sanitized.loc[sanitized["timestamp"] == origin, "p_load"].iloc[0] == 0.0


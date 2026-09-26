"""
Unit tests for Telemetry Data Loader and Source Abstraction.
"""

from pathlib import Path
import tempfile

import pandas as pd
import pytest

from ml_service.config import MicrogridConfig
from ml_service.data.loader import (
    REQUIRED_COLUMNS,
    CSVTelemetrySource,
    SyntheticTelemetrySource,
    get_telemetry_source,
)


def test_synthetic_telemetry_source_contract():
    config = MicrogridConfig(random_seed=42)
    source = SyntheticTelemetrySource(config)

    df = source.load_telemetry()
    assert isinstance(df, pd.DataFrame)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns
    assert len(df) == 8760

    # Test temporal filtering
    start = "2026-03-01 00:00:00"
    end = "2026-03-02 23:00:00"
    filtered = source.load_telemetry(start_time=start, end_time=end)
    assert len(filtered) == 48
    assert filtered["timestamp"].min() == pd.Timestamp(start)
    assert filtered["timestamp"].max() == pd.Timestamp(end)


def test_csv_telemetry_source_valid_and_invalid():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test_telemetry.csv"

        # Valid CSV
        valid_df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=24, freq="h"),
            "ghi": [0.0] * 24,
            "temp_amb": [20.0] * 24,
            "cloud_cover": [10.0] * 24,
            "p_pv": [0.0] * 24,
            "p_load": [15.0] * 24,
        })
        valid_df.to_csv(csv_path, index=False)

        config = MicrogridConfig(telemetry_source_type="csv", csv_telemetry_path=str(csv_path))
        source = CSVTelemetrySource(config, csv_path=csv_path)
        loaded = source.load_telemetry()
        assert len(loaded) == 24
        assert list(loaded.columns) == REQUIRED_COLUMNS

        # Invalid CSV missing required column
        bad_csv_path = Path(tmpdir) / "bad_telemetry.csv"
        bad_df = valid_df.drop(columns=["p_load"])
        bad_df.to_csv(bad_csv_path, index=False)

        bad_source = CSVTelemetrySource(config, csv_path=bad_csv_path)
        with pytest.raises(ValueError, match="missing required columns"):
            bad_source.load_telemetry()


def test_get_telemetry_source_factory():
    config_synth = MicrogridConfig(telemetry_source_type="synthetic")
    source_synth = get_telemetry_source(config_synth)
    assert isinstance(source_synth, SyntheticTelemetrySource)

    config_csv = MicrogridConfig(telemetry_source_type="csv")
    source_csv = get_telemetry_source(config_csv)
    assert isinstance(source_csv, CSVTelemetrySource)

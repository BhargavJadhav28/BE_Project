"""
Unit tests for Synthetic Telemetry Physics and Boundary Sanity.
"""

import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig
from ml_service.data.synthetic_generator import generate_synthetic_telemetry


def test_synthetic_data_structure_and_continuity():
    config = MicrogridConfig()
    df = generate_synthetic_telemetry(config)

    assert len(df) == 8760
    assert not df.isna().any().any()

    # Verify contiguous 1-hour time differences
    diffs = df["timestamp"].diff().dropna()
    assert (diffs == pd.Timedelta(hours=1)).all()


def test_solar_physics_and_bounds():
    config = MicrogridConfig(pv_peak_kw=50.0)
    df = generate_synthetic_telemetry(config)

    # 1. Nocturnal hours (e.g. 01:00) must have 0 GHI and 0 PV
    night_mask = df["timestamp"].dt.hour.isin([0, 1, 2, 3, 23])
    assert (df.loc[night_mask, "ghi"] == 0.0).all()
    assert (df.loc[night_mask, "p_pv"] == 0.0).all()

    # 2. Maximum PV cannot exceed rated inverter capacity
    assert df["p_pv"].max() <= config.pv_peak_kw
    assert df["p_pv"].min() >= 0.0

    # 3. Summer noon solar should generate substantial power (> 20 kW)
    summer_noon = (df["timestamp"].dt.month == 6) & (df["timestamp"].dt.hour == 12)
    assert df.loc[summer_noon, "p_pv"].mean() > 20.0


def test_load_demand_physics_and_peaks():
    config = MicrogridConfig(base_load_kw=10.0, load_peak_kw=45.0)
    df = generate_synthetic_telemetry(config)

    # Bounds
    assert df["p_load"].min() >= config.base_load_kw - 1e-3
    assert df["p_load"].max() <= config.load_peak_kw + 1e-3

    # Dual peak profile: morning (7-9) and evening (18-21) vs nocturnal (1-4)
    night_load = df.loc[df["timestamp"].dt.hour.isin([1, 2, 3, 4]), "p_load"].mean()
    morning_load = df.loc[df["timestamp"].dt.hour.isin([7, 8, 9]), "p_load"].mean()
    evening_load = df.loc[df["timestamp"].dt.hour.isin([18, 19, 20]), "p_load"].mean()

    assert morning_load > night_load + 5.0
    assert evening_load > morning_load

"""
Deterministic Synthetic Telemetry Generator for Microgrids.

Calibrated to the NREL NSRDB Pune Climate Baseline (Latitude 18.55 N):
- Solar Geometry & Clear-Sky Irradiance (GHI, W/m^2) at Latitude 18.55 N
- Ambient Temperature (T_amb, deg C) calibrated to Pune range [12.0, 43.5] deg C
- Cloud Cover (0-100%) with seasonal monsoon depressions (days 160 to 260)
- Solar PV Generation (P_pv, kW) with thermal derating and inverter efficiency
- Load Demand (P_load, kW) with commercial schedule, weekend discount, HVAC cooling,
  and heavy-tailed industrial motor inrush spikes
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig


def generate_synthetic_telemetry(
    config: MicrogridConfig = MicrogridConfig(),
    start_date: str = "2026-01-01 00:00:00",
    hours: int = 8760,
) -> pd.DataFrame:
    """Generate 1 year of hourly deterministic synthetic microgrid telemetry.

    Schema: ['timestamp', 'ghi', 'temp_amb', 'cloud_cover', 'p_pv', 'p_load']
    """
    rng = np.random.default_rng(config.random_seed)

    # 1. Temporal Index (hourly continuous)
    timestamps = pd.date_range(start=start_date, periods=hours, freq="h")
    hours_arr = timestamps.hour.to_numpy()
    days_arr = timestamps.dayofyear.to_numpy()
    day_of_week = timestamps.dayofweek.to_numpy()  # 5=Sat, 6=Sun

    # 2. Solar Geometry & Clear-Sky GHI (Calibrated to Pune Latitude 18.55 deg N)
    # Solar declination angle delta (Spencer / Cooper empirical formula)
    delta = np.deg2rad(23.45 * np.sin(2.0 * np.pi * (284.0 + days_arr) / 365.25))

    # Solar hour angle omega: 15 deg per hour from solar noon (12:00)
    omega = np.deg2rad(15.0 * (hours_arr - 12.0))

    # Reference latitude: Pune microgrid at 18.55 deg N
    phi = np.deg2rad(18.55)

    # Cosine of solar zenith angle cos(theta_z)
    cos_zenith = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(omega)
    cos_zenith = np.maximum(0.0, cos_zenith)

    # Clear-sky irradiance at latitude 18.55 N
    clear_sky_ghi = np.where(cos_zenith > 0.0, 1050.0 * np.power(cos_zenith, 1.15), 0.0)

    # 3. Cloud Cover (Markov Autoregressive process with Monsoon Depression Regime)
    cloud_cover = np.zeros(hours, dtype=np.float64)
    c_prev = 20.0
    rho = 0.88  # Autoregressive persistence
    cloud_noise = rng.normal(loc=0.0, scale=12.0, size=hours)

    for t in range(hours):
        d = days_arr[t]
        # Seasonal monsoon depression regime for days 160 to 260 (June - August)
        monsoon_boost = 32.0 if (160 <= d <= 260) else 0.0
        season_mean = 20.0 + 8.0 * np.sin(2.0 * np.pi * (d - 80.0) / 365.25) + monsoon_boost
        c_val = rho * c_prev + (1.0 - rho) * season_mean + cloud_noise[t]
        c_val = float(np.clip(c_val, 0.0, 100.0))
        cloud_cover[t] = c_val
        c_prev = c_val

    # Actual GHI attenuated by cloud cover
    cloud_factor = 1.0 - 0.75 * (cloud_cover / 100.0)
    ghi = clear_sky_ghi * cloud_factor
    ghi = np.where(cos_zenith <= 0.0, 0.0, np.maximum(0.0, ghi))

    # 4. Ambient Temperature (Calibrated to Pune observations [12.0, 43.5] deg C)
    # Seasonal baseline: peaks in April/May (day ~110), minimum in Dec/Jan
    temp_seasonal = 24.0 + 7.5 * np.sin(2.0 * np.pi * (days_arr - 75.0) / 365.25)
    # Diurnal variation: ~8 deg C amplitude peaking at 15:00
    temp_diurnal = (8.0 - 2.5 * (cloud_cover / 100.0)) * np.cos(2.0 * np.pi * (hours_arr - 15.0) / 24.0)
    # Monsoon evaporative cooling depression for days 160 to 260
    monsoon_cooling = np.where((days_arr >= 160) & (days_arr <= 260), -4.5 * (cloud_cover / 100.0), 0.0)
    temp_noise = rng.normal(loc=0.0, scale=0.8, size=hours)
    temp_amb = np.clip(temp_seasonal + temp_diurnal + monsoon_cooling + temp_noise, 10.0, 45.0)

    # 5. Solar PV Generation (Thermal derating and Sandia inverter efficiency)
    thermal_derating = 1.0 - 0.004 * (temp_amb - 25.0)
    thermal_derating = np.clip(thermal_derating, 0.70, 1.10)

    p_dc = config.pv_peak_kw * (ghi / 1000.0) * thermal_derating
    p_loss = np.where(p_dc > 0.10, 0.10 + 0.018 * p_dc + 0.0004 * (p_dc ** 2), p_dc)
    p_ac = np.maximum(0.0, p_dc - p_loss)
    p_pv = np.where(ghi <= 0.0, 0.0, np.clip(p_ac, 0.0, config.pv_peak_kw))

    # 6. Load Demand (Commercial diurnal, 18% weekend discount, HVAC cooling, inrush spikes)
    diurnal_profile = np.array([
        0.05, 0.03, 0.02, 0.02, 0.03, 0.06,  # 00-05: Nocturnal baseline
        0.25, 0.50, 0.68, 0.75,              # 06-09: Morning ramp
        0.78, 0.80, 0.76, 0.75, 0.78, 0.82, 0.85, 0.88,  # 10-17: Business operations
        0.95, 1.00, 0.98, 0.88, 0.70,        # 18-22: Evening peak
        0.25                                 # 23: Wind-down
    ])
    diurnal_factor = diurnal_profile[hours_arr]

    # Weekend discount: 18% reduction on Sat/Sun
    is_weekend = np.isin(day_of_week, [5, 6])
    weekend_factor = np.where(is_weekend, 0.82, 1.0)

    # Pune HVAC Cooling load (triggered when temp > 24.0 deg C)
    hvac_load = np.maximum(0.0, (temp_amb - 24.0) * 0.75)

    # Nominal dynamic load span
    nominal_span = config.load_peak_kw - config.base_load_kw - 8.0
    base_dynamic_load = config.base_load_kw + (nominal_span * diurnal_factor * weekend_factor)

    # Asymmetric industrial motor inrush spikes during work hours (weekdays 08:00 - 17:00)
    is_work_hour = (~is_weekend) & (hours_arr >= 8) & (hours_arr <= 17)
    has_spike = is_work_hour & (rng.random(hours) < 0.20)
    raw_spikes = rng.lognormal(mean=1.75, sigma=0.35, size=hours)
    spikes = np.where(has_spike, np.clip(raw_spikes, 4.0, 10.0), 0.0)

    load_noise = rng.normal(loc=0.0, scale=0.8, size=hours)
    max_load_transient = 1.2 * config.load_peak_kw  # 54.0 kW

    p_load = base_dynamic_load + hvac_load + spikes + load_noise
    p_load = np.clip(p_load, config.base_load_kw, max_load_transient)

    return pd.DataFrame({
        "timestamp": timestamps,
        "ghi": np.round(ghi, 2),
        "temp_amb": np.round(temp_amb, 2),
        "cloud_cover": np.round(cloud_cover, 2),
        "p_pv": np.round(p_pv, 3),
        "p_load": np.round(p_load, 3),
    })

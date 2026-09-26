"""
Deterministic Synthetic Telemetry Generator for Microgrids.

Generates 1 continuous year (8,760 hours) of physically grounded hourly data:
- Solar Zenith & Irradiance (GHI, W/m^2)
- Ambient Temperature (T_amb, deg C)
- Cloud Cover (0-100%)
- Solar PV Generation (P_pv, kW) with thermal derating
- Load Demand (P_load, kW) with dual diurnal peaks, weekend discount, and HVAC thermal load
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
    day_of_week = timestamps.dayofweek.to_numpy() # 5=Sat, 6=Sun

    # 2. Solar Geometry & Clear-Sky GHI
    # Solar declination angle delta (approximate Spencer / Cooper formula)
    # delta = 23.45 * sin(2*pi*(284 + n) / 365) in radians
    delta = np.deg2rad(23.45 * np.sin(2.0 * np.pi * (284.0 + days_arr) / 365.25))

    # Solar hour angle omega: 15 deg per hour from solar noon (12:00)
    omega = np.deg2rad(15.0 * (hours_arr - 12.0))

    # Reference latitude (sub-tropical microgrid ~25 deg N)
    phi = np.deg2rad(25.0)

    # Cosine of solar zenith angle cos(theta_z)
    cos_zenith = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(omega)
    cos_zenith = np.maximum(0.0, cos_zenith)

    # Clear-sky irradiance: 0 at night, up to ~1000 W/m^2 at solar noon in summer
    # Using empirical exponent ~1.15 to model atmospheric path length
    clear_sky_ghi = np.where(cos_zenith > 0.0, 1000.0 * np.power(cos_zenith, 1.15), 0.0)

    # 3. Cloud Cover (Autoregressive Markov process bounded in [0, 100])
    # Simulates weather front transitions and intermittency
    cloud_cover = np.zeros(hours, dtype=np.float64)
    c_prev = 25.0
    rho = 0.88 # High autoregressive persistence
    cloud_noise = rng.normal(loc=0.0, scale=12.0, size=hours)

    for t in range(hours):
        # Mean reverting around seasonal baseline
        season_mean = 28.0 + 10.0 * np.sin(2.0 * np.pi * days_arr[t] / 365.25)
        c_val = rho * c_prev + (1.0 - rho) * season_mean + cloud_noise[t]
        c_val = float(np.clip(c_val, 0.0, 100.0))
        cloud_cover[t] = c_val
        c_prev = c_val

    # Actual GHI attenuated by cloud cover
    cloud_factor = 1.0 - 0.75 * (cloud_cover / 100.0)
    ghi = clear_sky_ghi * cloud_factor
    ghi = np.where(cos_zenith <= 0.0, 0.0, np.maximum(0.0, ghi))

    # 4. Ambient Temperature (Sinusoidal curve peaking at 15:00, 3h after solar noon)
    # Seasonal baseline: -2 deg C (winter) to 34 deg C (summer)
    temp_seasonal = 18.0 + 14.0 * np.sin(2.0 * np.pi * (days_arr - 105.0) / 365.25)
    # Diurnal variation: ~7 deg C amplitude, peak at 15:00
    temp_diurnal = (7.0 - 2.0 * (cloud_cover / 100.0)) * np.cos(2.0 * np.pi * (hours_arr - 15.0) / 24.0)
    temp_noise = rng.normal(loc=0.0, scale=0.8, size=hours)
    temp_amb = np.clip(temp_seasonal + temp_diurnal + temp_noise, -5.0, 42.0)

    # 5. Solar PV Generation (Incorporates thermal derating)
    # Thermal derating gamma = 0.004 (0.4% loss per deg C above 25 deg C)
    thermal_derating = 1.0 - 0.004 * (temp_amb - 25.0)
    thermal_derating = np.clip(thermal_derating, 0.70, 1.10)

    # Inverter rating clipping and night zeroing
    p_pv = config.pv_peak_kw * (ghi / 1000.0) * thermal_derating
    p_pv = np.where(ghi <= 0.0, 0.0, np.clip(p_pv, 0.0, config.pv_peak_kw))

    # 6. Load Demand (Dual-peak diurnal, weekend discount, HVAC thermal load)
    # Base diurnal profile:
    # 00-06: nocturnal base
    # 07-09: morning ramp
    # 10-17: daytime commercial/industrial
    # 18-22: evening peak
    # 23: wind-down
    diurnal_profile = np.array([
        0.28, 0.25, 0.24, 0.24, 0.26, 0.32,  # 00-05
        0.50, 0.75, 0.85, 0.78, 0.72, 0.70,  # 06-11
        0.68, 0.67, 0.69, 0.72, 0.76, 0.82,  # 12-17
        0.95, 1.00, 0.92, 0.78, 0.55, 0.38   # 18-23
    ])
    diurnal_factor = diurnal_profile[hours_arr]

    # Weekend discount: ~20% reduction on Sat/Sun
    is_weekend = np.isin(day_of_week, [5, 6])
    weekend_factor = np.where(is_weekend, 0.82, 1.0)

    # HVAC Thermal Sensitivity:
    # Cooling load when temp > 22 deg C; heating load when temp < 16 deg C
    cooling_load = np.maximum(0.0, temp_amb - 22.0) * 0.45
    heating_load = np.maximum(0.0, 16.0 - temp_amb) * 0.35
    hvac_load = cooling_load + heating_load

    # Nominal load synthesis
    load_span = config.load_peak_kw - config.base_load_kw - 8.0 # reserve headroom for HVAC/noise
    base_dynamic_load = config.base_load_kw + (load_span * diurnal_factor * weekend_factor)
    load_noise = rng.normal(loc=0.0, scale=1.5, size=hours)

    p_load = base_dynamic_load + hvac_load + load_noise
    p_load = np.clip(p_load, config.base_load_kw, config.load_peak_kw)

    return pd.DataFrame({
        "timestamp": timestamps,
        "ghi": np.round(ghi, 2),
        "temp_amb": np.round(temp_amb, 2),
        "cloud_cover": np.round(cloud_cover, 2),
        "p_pv": np.round(p_pv, 3),
        "p_load": np.round(p_load, 3),
    })

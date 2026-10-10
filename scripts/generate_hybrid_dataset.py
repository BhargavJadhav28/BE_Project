"""
Microgrid Asset Power Synthesizer and Hybrid Dataset Generator.

Phase 2 of the Ultimate Dataset Migration:
1. Loads aligned NSRDB weather telemetry (Pune, Lat 18.55 N).
2. Computes module cell temperature with wind convective cooling.
3. Computes active solar PV generation (P_pv) with thermal derating, panel soiling,
   and non-linear Sandia inverter efficiency clipping.
4. Synthesizes realistic facility electrical load (P_load) with commercial diurnal schedule,
   weekend discounts, Pune HVAC cooling response, and industrial motor inrush spikes.
5. Saves the production telemetry artifact to data/raw_telemetry.csv.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# Allow running as script or module
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_service.config import MicrogridConfig
from scripts.process_nsrdb_telemetry import process_nsrdb_telemetry


def compute_solar_pv_generation(
    ghi: np.ndarray,
    temp_amb: np.ndarray,
    wind_speed: np.ndarray,
    dni: np.ndarray,
    dhi: np.ndarray,
    months: np.ndarray,
    dew_point: np.ndarray,
    config: MicrogridConfig = MicrogridConfig(),
    seed: int = 42,
) -> np.ndarray:
    """Compute active solar photovoltaic generation (P_pv, kW).

    Formulations:
    - Cell temperature with convective wind cooling:
      T_cell = T_amb + GHI * exp(-3.47 - 0.0594 * v_wind)
    - Silicon thermal derating:
      gamma = -0.4% / deg C above 25 deg C
    - Dynamic panel soiling with monsoon rain cleaning:
      +0.15% / day dry accumulation (up to 6.0%), resets to 0.0% during rain
    - Sandia non-linear inverter efficiency:
      Quadratic loss curve with tare threshold, clipped to [0.0, pv_peak_kw]
    """
    n_samples = len(ghi)
    rng = np.random.default_rng(seed)

    # 1. Physical Cell Temperature with Wind Cooling
    # T_cell = T_amb + GHI * exp(-3.47 - 0.0594 * v_wind)
    wind_cooling_factor = np.exp(-3.47 - 0.0594 * wind_speed)
    t_cell = temp_amb + ghi * wind_cooling_factor

    # Silicon thermal derating (-0.4% / deg C above 25 deg C)
    thermal_derating = 1.0 - 0.004 * (t_cell - 25.0)
    thermal_derating = np.clip(thermal_derating, 0.65, 1.15)

    # 2. Panel Soiling and Rain Cleaning Factor (S_soil)
    # Group by 24-hour day to track daily soiling accumulation and rain washing
    n_days = n_samples // 24
    daily_soiling = []
    current_soiling = 0.02  # Initial modest dry-season dust layer

    for d in range(n_days):
        idx_start = d * 24
        idx_end = idx_start + 24
        m = months[idx_start]
        day_ghi = ghi[idx_start:idx_end]
        day_dew = dew_point[idx_start:idx_end].mean()

        daylight_ghi = day_ghi[day_ghi > 0]
        mean_daylight_ghi = daylight_ghi.mean() if len(daylight_ghi) > 0 else 0.0

        # Monsoon rain condition: June-September (months 6 to 9) with heavy overcast or high dew point
        is_monsoon_rain = (m in [6, 7, 8, 9]) and (mean_daylight_ghi < 250.0 or day_dew > 21.0)

        if is_monsoon_rain:
            current_soiling = 0.0  # Rain cleans panel glass
        else:
            current_soiling = min(0.06, current_soiling + 0.0015)  # +0.15% daily accumulation, cap at 6.0%

        daily_soiling.append(current_soiling)

    soiling_factor = np.repeat(np.array(daily_soiling), 24)
    if len(soiling_factor) < n_samples:
        soiling_factor = np.pad(soiling_factor, (0, n_samples - len(soiling_factor)), mode="edge")

    # 3. Direct/Diffuse Atmospheric Composition & MPPT Variation
    # Realistic operational micro-fluctuations (sub-hourly cloud edges, sensor uncertainty)
    diffuse_ratio = np.where(ghi > 0.0, dhi / np.maximum(1.0, ghi), 0.0)
    aoi_loss = 0.04 * (1.0 - diffuse_ratio)  # Reflection losses on direct beam at grazing angles
    mppt_tracking_jitter = rng.normal(0.0, 0.035, size=n_samples)  # Realistic inverter MPPT tracking ripple
    irradiance_ripple = rng.normal(0.0, 1.8, size=n_samples) * (ghi / 1000.0)

    # 4. DC Power Output
    p_dc = (
        config.pv_peak_kw
        * (ghi / 1000.0)
        * (1.0 - aoi_loss)
        * thermal_derating
        * (1.0 - soiling_factor)
        * (1.0 + mppt_tracking_jitter)
        + irradiance_ripple
    )
    p_dc = np.maximum(0.0, p_dc)

    # 5. Non-Linear Inverter Conversion Efficiency (Sandia Curve)
    # Real inverters suffer tare losses at low power and resistive losses at high load
    p_loss = np.where(p_dc > 0.10, 0.10 + 0.018 * p_dc + 0.0004 * (p_dc ** 2), p_dc)
    p_ac = np.maximum(0.0, p_dc - p_loss)

    # Nocturnal zeroing and rated inverter clipping
    p_pv = np.where(ghi <= 0.0, 0.0, np.clip(p_ac, 0.0, config.pv_peak_kw))
    return np.round(p_pv, 3)


def compute_facility_load_demand(
    timestamps: pd.DatetimeIndex,
    temp_amb: np.ndarray,
    config: MicrogridConfig = MicrogridConfig(),
    seed: int = 42,
) -> np.ndarray:
    """Compute realistic facility electrical load demand (P_load, kW).

    Formulations:
    - Base diurnal commercial profile:
      00:00 - 05:00: Nocturnal baseline (10.0 to 12.0 kW)
      06:00 - 09:00: Morning startup ramp
      10:00 - 17:00: Primary business operations (28.0 to 34.0 kW)
      18:00 - 22:00: Evening lighting and domestic peak (38.0 to 45.0 kW)
      Weekend discount: 18.0% reduction on Saturday and Sunday
    - Pune climate HVAC cooling load:
      P_hvac = max(0.0, (T_amb - 24.0) * 0.75)
    - Heavy-tailed industrial inrush spikes:
      Log-normal power impulses (+4.0 kW to +10.0 kW) during work hours
    - Transient ceiling enforced at P_load_max = 54.0 kW, minimum 10.0 kW
    """
    n_samples = len(timestamps)
    rng = np.random.default_rng(seed)

    hours_arr = timestamps.dt.hour.to_numpy() if hasattr(timestamps, "dt") else timestamps.hour.to_numpy()
    dow_arr = timestamps.dt.dayofweek.to_numpy() if hasattr(timestamps, "dt") else timestamps.dayofweek.to_numpy()
    is_weekend = np.isin(dow_arr, [5, 6])

    # 1. Base Diurnal Commercial Profile (kW)
    # Reflects commercial schedule with night baseline, daytime operations, and evening peak
    base_profile = np.array([
        10.8, 10.5, 10.2, 10.2, 10.5, 11.2,  # 00-05: Nocturnal baseline
        16.0, 23.0, 28.5, 30.5,              # 06-09: Morning startup ramp
        31.5, 32.0, 31.0, 30.8, 31.2, 32.5, 33.5, 34.0,  # 10-17: Business operations
        39.0, 41.5, 41.0, 38.5, 32.0,        # 18-22: Evening peak
        16.5                                 # 23: Wind-down
    ])

    # 18.0% load discount on Saturday and Sunday for dynamic operational load
    weekend_factor = np.where(is_weekend, 0.82, 1.0)
    base_load = config.base_load_kw + (base_profile[hours_arr] - config.base_load_kw) * weekend_factor

    # 2. Pune Climate HVAC Cooling Load
    # Commercial cooling demand triggered above 24.0 deg C (adds up to 16.5 kW at 46 deg C)
    hvac_load = np.maximum(0.0, (temp_amb - 24.0) * 0.75)

    # 3. Heavy-Tailed Industrial Inrush Spikes
    # Motor, pump, and compressor startup impulses during working hours (weekdays 08:00 - 17:00)
    is_work_hour = (~is_weekend) & (hours_arr >= 8) & (hours_arr <= 17)
    has_spike = is_work_hour & (rng.random(n_samples) < 0.22)
    raw_spikes = rng.lognormal(mean=1.75, sigma=0.35, size=n_samples)
    spikes = np.where(has_spike, np.clip(raw_spikes, 4.0, 10.0), 0.0)

    # Continuous stochastic load variations
    noise = rng.normal(loc=0.0, scale=1.4, size=n_samples)

    # Hard transient ceiling enforced at P_load_max = 54.0 kW (1.2 * 45 kW)
    max_transient_limit = 1.2 * config.load_peak_kw
    p_load = np.clip(base_load + hvac_load + spikes + noise, config.base_load_kw, max_transient_limit)

    return np.round(p_load, 3)


def generate_hybrid_dataset(
    raw_weather_df: pd.DataFrame,
    config: MicrogridConfig = MicrogridConfig(),
    seed: int = 42,
) -> pd.DataFrame:
    """Combine real atmospheric observations with high-fidelity asset physics into standard telemetry.

    Output Schema: ['timestamp', 'ghi', 'temp_amb', 'cloud_cover', 'p_pv', 'p_load']
    """
    timestamps = pd.to_datetime(raw_weather_df["timestamp"])
    months = timestamps.dt.month.to_numpy()

    ghi = raw_weather_df["ghi"].to_numpy().astype(np.float64)
    temp_amb = raw_weather_df["temp_amb"].to_numpy().astype(np.float64)
    wind_speed = raw_weather_df["wind_speed"].to_numpy().astype(np.float64)
    dni = raw_weather_df["dni"].to_numpy().astype(np.float64)
    dhi = raw_weather_df["dhi"].to_numpy().astype(np.float64)
    dew_point = raw_weather_df["dew_point"].to_numpy().astype(np.float64)
    cloud_cover = raw_weather_df["cloud_cover"].to_numpy().astype(np.float64)

    # Synthesize P_pv and P_load
    p_pv = compute_solar_pv_generation(
        ghi=ghi,
        temp_amb=temp_amb,
        wind_speed=wind_speed,
        dni=dni,
        dhi=dhi,
        months=months,
        dew_point=dew_point,
        config=config,
        seed=seed,
    )

    p_load = compute_facility_load_demand(
        timestamps=timestamps,
        temp_amb=temp_amb,
        config=config,
        seed=seed,
    )

    output_df = pd.DataFrame({
        "timestamp": timestamps,
        "ghi": np.round(ghi, 2),
        "temp_amb": np.round(temp_amb, 2),
        "cloud_cover": np.round(cloud_cover, 2),
        "p_pv": np.round(p_pv, 3),
        "p_load": np.round(p_load, 3),
    })

    return output_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Ultimate Hybrid Microgrid Telemetry Dataset.")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="22575_18.55_73.85_tmy.csv",
        help="Path to raw NSRDB TMY CSV file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/raw_telemetry.csv",
        help="Target output CSV path for standardized microgrid telemetry.",
    )
    parser.add_argument(
        "--year",
        "-y",
        type=int,
        default=2026,
        help="Reference calendar year for continuous hourly grid.",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    print(f"Phase 1: Ingesting and aligning NSRDB Pune weather records from {input_path}...")
    weather_df = process_nsrdb_telemetry(input_path, reference_year=args.year)

    print("Phase 2: Synthesizing physics-informed PV generation and facility load telemetry...")
    config = MicrogridConfig()
    hybrid_df = generate_hybrid_dataset(weather_df, config=config, seed=args.seed)

    print(f"\nGenerated Hybrid Dataset Summary ({len(hybrid_df)} hours):")
    print(f"• GHI: min={hybrid_df['ghi'].min():.1f}, max={hybrid_df['ghi'].max():.1f}, mean={hybrid_df['ghi'].mean():.1f} W/m^2")
    print(f"• Ambient Temp: min={hybrid_df['temp_amb'].min():.1f}, max={hybrid_df['temp_amb'].max():.1f}, mean={hybrid_df['temp_amb'].mean():.1f} C")
    print(f"• Cloud Cover: min={hybrid_df['cloud_cover'].min():.1f}%, max={hybrid_df['cloud_cover'].max():.1f}%, mean={hybrid_df['cloud_cover'].mean():.1f}%")
    print(f"• Solar PV (P_pv): min={hybrid_df['p_pv'].min():.1f}, max={hybrid_df['p_pv'].max():.1f}, mean={hybrid_df['p_pv'].mean():.1f} kW")
    print(f"• Facility Load (P_load): min={hybrid_df['p_load'].min():.1f}, max={hybrid_df['p_load'].max():.1f}, mean={hybrid_df['p_load'].mean():.1f} kW")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    hybrid_df.to_csv(output_path, index=False)
    print(f"\nSuccessfully written production telemetry to {output_path}.")


if __name__ == "__main__":
    main()

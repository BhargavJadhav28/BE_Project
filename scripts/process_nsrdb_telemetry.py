"""
NSRDB Pune Weather Data Ingestion and Alignment Script.

Phase 1 of the Ultimate Dataset Migration:
1. Ingests raw NREL NSRDB TMY CSV data for Pune (Lat 18.55 N, Long 73.85 E).
2. Parses date components (Year, Month, Day, Hour, Minute).
3. Snaps half-hour intervals (:30) to the strict hourly UTC grid (:00) for 8,760 hours.
4. Computes clear-sky irradiance (GHI_clear), Clearness Index (k_t), and derives cloud_cover.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional

import numpy as np
import pandas as pd

# Allow running as script or module
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def compute_clearsky_ghi(
    days_of_year: np.ndarray,
    hours_of_day: np.ndarray,
    latitude_deg: float = 18.55,
) -> np.ndarray:
    """Compute theoretical clear-sky Global Horizontal Irradiance (GHI_clear).

    Parameters
    ----------
    days_of_year : np.ndarray
        Day of the year (1 to 365).
    hours_of_day : np.ndarray
        Hour of the day (0 to 23).
    latitude_deg : float
        Geographic latitude in degrees (18.55 deg N for Pune).

    Returns
    -------
    np.ndarray
        Theoretical clear-sky GHI in W/m^2.
    """
    phi = np.deg2rad(latitude_deg)

    # Solar declination angle delta (Spencer / Cooper empirical formulation)
    delta = np.deg2rad(23.45 * np.sin(2.0 * np.pi * (284.0 + days_of_year) / 365.25))

    # Solar hour angle omega: 15 deg per hour from solar noon (12:00)
    omega = np.deg2rad(15.0 * (hours_of_day - 12.0))

    # Cosine of solar zenith angle cos(theta_z)
    cos_zenith = np.maximum(0.0, np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(omega))

    # Clear-sky irradiance with atmospheric path exponent ~1.15
    ghi_clear = np.where(cos_zenith > 0.0, 1050.0 * np.power(cos_zenith, 1.15), 0.0)
    return ghi_clear


def derive_cloud_cover(
    ghi: np.ndarray,
    ghi_clear: np.ndarray,
    min_daylight_irradiance: float = 15.0,
) -> np.ndarray:
    """Derive percentage cloud cover from Clearness Index (k_t) with smooth nocturnal interpolation.

    Parameters
    ----------
    ghi : np.ndarray
        Observed Global Horizontal Irradiance in W/m^2.
    ghi_clear : np.ndarray
        Theoretical clear-sky Irradiance in W/m^2.
    min_daylight_irradiance : float
        Irradiance threshold to isolate daytime clearness calculations.

    Returns
    -------
    np.ndarray
        Continuous cloud cover percentages bounded in [0.0, 100.0].
    """
    n_samples = len(ghi)
    daylight_mask = (ghi_clear > min_daylight_irradiance) & (ghi > 0.0)

    cloud_raw = np.full(n_samples, np.nan, dtype=np.float64)

    # Clearness index k_t = GHI / GHI_clear
    safe_ghi_clear = np.where(daylight_mask, ghi_clear, 1.0)
    kt = np.where(daylight_mask, ghi / safe_ghi_clear, np.nan)

    # Standard atmospheric attenuation relation: Cloud = (1.0 - k_t) * 100%
    cloud_raw[daylight_mask] = np.clip((1.0 - kt[daylight_mask]) * 100.0, 0.0, 100.0)

    # Smooth linear interpolation across nocturnal gaps (between sunset and sunrise)
    cloud_series = pd.Series(cloud_raw).interpolate(method="linear").bfill().ffill()
    return np.clip(cloud_series.to_numpy(), 0.0, 100.0)


def process_nsrdb_telemetry(
    csv_path: str | Path,
    reference_year: int = 2026,
) -> pd.DataFrame:
    """Ingest and align NSRDB Pune weather records to a strict hourly grid.

    Parameters
    ----------
    csv_path : str or Path
        Path to NSRDB TMY CSV file (contains metadata header rows).
    reference_year : int
        Calendar year for temporal indexing (default: 2026).

    Returns
    -------
    pd.DataFrame
        Aligned dataframe containing timestamp, GHI, DNI, DHI, Temperature,
        Wind Speed, Dew Point, clear_sky_ghi, and cloud_cover.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"NSRDB CSV file not found: {path}")

    # NSRDB CSV files have 2 metadata header rows, data starts at line 3 (index 2)
    raw_df = pd.read_csv(path, skiprows=2)

    required_cols = ["Year", "Month", "Day", "Hour", "Minute", "GHI", "DNI", "DHI", "Temperature", "Wind Speed"]
    missing = [c for c in required_cols if c not in raw_df.columns]
    if missing:
        raise ValueError(f"NSRDB CSV missing required columns: {missing}")

    n_records = len(raw_df)
    if n_records != 8760:
        print(f"Warning: Expected 8760 hourly records, found {n_records}.")

    # 1. Snap half-hour samples (:30) to the strict hourly UTC grid (:00)
    timestamps = pd.date_range(f"{reference_year}-01-01 00:00:00", periods=n_records, freq="h")
    days_of_year = timestamps.dayofyear.to_numpy()
    hours_of_day = timestamps.hour.to_numpy()

    ghi = raw_df["GHI"].to_numpy().astype(np.float64)
    dni = raw_df["DNI"].to_numpy().astype(np.float64)
    dhi = raw_df["DHI"].to_numpy().astype(np.float64)
    temp = raw_df["Temperature"].to_numpy().astype(np.float64)
    wind_speed = raw_df["Wind Speed"].to_numpy().astype(np.float64)
    dew_point = raw_df["Dew Point"].to_numpy().astype(np.float64) if "Dew Point" in raw_df.columns else np.zeros(n_records)

    # 2. Compute Clear-Sky GHI and derived Cloud Cover
    ghi_clear = compute_clearsky_ghi(days_of_year, hours_of_day, latitude_deg=18.55)
    cloud_cover = derive_cloud_cover(ghi, ghi_clear)

    aligned_df = pd.DataFrame({
        "timestamp": timestamps,
        "ghi": np.round(ghi, 2),
        "dni": np.round(dni, 2),
        "dhi": np.round(dhi, 2),
        "temp_amb": np.round(temp, 2),
        "wind_speed": np.round(wind_speed, 2),
        "dew_point": np.round(dew_point, 2),
        "ghi_clear": np.round(ghi_clear, 2),
        "cloud_cover": np.round(cloud_cover, 2),
    })

    return aligned_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Process and align NSRDB Pune weather telemetry.")
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
        default=None,
        help="Optional path to save aligned weather CSV.",
    )
    parser.add_argument(
        "--year",
        "-y",
        type=int,
        default=2026,
        help="Reference calendar year for continuous hourly grid.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    print(f"Processing NSRDB telemetry from {input_path}...")
    df = process_nsrdb_telemetry(input_path, reference_year=args.year)
    print(f"Successfully processed {len(df)} hourly weather records.")
    print(f"Irradiance: GHI max={df['ghi'].max():.1f} W/m^2, mean={df['ghi'].mean():.1f} W/m^2")
    print(f"Temperature: min={df['temp_amb'].min():.1f} C, max={df['temp_amb'].max():.1f} C")
    print(f"Cloud Cover: min={df['cloud_cover'].min():.1f}%, max={df['cloud_cover'].max():.1f}%, mean={df['cloud_cover'].mean():.1f}%")

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"Saved aligned weather data to {out_path}.")


if __name__ == "__main__":
    main()

"""
Origin-Anchored Feature Engineering Pipeline.

Extracts tabular features for 24-hour horizon-conditioned regression:
- Origin-anchored lags frozen at forecast origin T (P(T), P(T-1), P(T-23), P(T-24))
- Rolling 6-hour and 24-hour summary statistics computed strictly on historical data <= T
- Forward horizon indicators (h in [1..24]) and cyclical temporal encodings for T+h
- Forward horizon weather forecasts (GHI, T_amb, CloudCover) and delta GHI for T+h
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig

PV_FEATURE_NAMES = [
    "horizon",
    "p_pv_lag_0",
    "p_pv_lag_1",
    "p_pv_lag_23",
    "p_pv_lag_24",
    "p_pv_mean_6h",
    "p_pv_std_6h",
    "p_pv_mean_24h",
    "p_pv_std_24h",
    "ghi_forecast",
    "delta_ghi",
    "temp_amb_forecast",
    "cloud_cover_forecast",
    "sin_hour",
    "cos_hour",
    "sin_day_of_year",
    "cos_day_of_year",
    "is_weekend",
]

LOAD_FEATURE_NAMES = [
    "horizon",
    "p_load_lag_0",
    "p_load_lag_1",
    "p_load_lag_23",
    "p_load_lag_24",
    "p_load_mean_6h",
    "p_load_std_6h",
    "p_load_mean_24h",
    "p_load_std_24h",
    "temp_amb_forecast",
    "sin_hour",
    "cos_hour",
    "sin_day_of_year",
    "cos_day_of_year",
    "is_weekend",
]


class FeaturePipeline:
    """Constructs origin-anchored tabular feature matrices for inference and evaluation."""

    def __init__(self, config: MicrogridConfig = MicrogridConfig()) -> None:
        self.config = config

    def extract_features_for_origin(
        self,
        origin: pd.Timestamp | str,
        sanitized_history_df: pd.DataFrame,
        weather_forecast_24h_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Construct the 24-row feature matrix for a single forecast origin T.

        Parameters
        ----------
        origin : pd.Timestamp | str
            Forecast origin timestamp T.
        sanitized_history_df : pd.DataFrame
            Sanitized telemetry spanning [T - 48h, T].
        weather_forecast_24h_df : pd.DataFrame
            Weather forecasts for the 24 future steps [T + 1h, T + 24h].
            Columns: ['timestamp', 'ghi', 'temp_amb', 'cloud_cover']

        Returns
        -------
        pd.DataFrame
            24 rows of aligned features.
        """
        origin_ts = pd.to_datetime(origin)
        if getattr(origin_ts, "tz", None) is not None:
            origin_ts = origin_ts.tz_convert("UTC").tz_localize(None)
        origin_ts = origin_ts.floor("h")

        # Standardize history index
        hist = sanitized_history_df.copy()
        if "timestamp" in hist.columns:
            hist["timestamp"] = pd.to_datetime(hist["timestamp"])
            if getattr(hist["timestamp"].dt, "tz", None) is not None:
                hist["timestamp"] = hist["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
            hist["timestamp"] = hist["timestamp"].dt.floor("h")
            hist = hist.set_index("timestamp")
        elif isinstance(hist.index, pd.DatetimeIndex):
            if hist.index.tz is not None:
                hist.index = hist.index.tz_convert("UTC").tz_localize(None)
            hist.index = hist.index.floor("h")
        hist = hist[~hist.index.duplicated(keep="last")].sort_index()

        # Origin-anchored lags at T
        # T, T-1, T-23, T-24
        ts_0 = origin_ts
        ts_1 = origin_ts - pd.Timedelta(hours=1)
        ts_23 = origin_ts - pd.Timedelta(hours=23)
        ts_24 = origin_ts - pd.Timedelta(hours=24)

        p_pv_0 = float(hist.loc[ts_0, "p_pv"])
        p_pv_1 = float(hist.loc[ts_1, "p_pv"])
        p_pv_23 = float(hist.loc[ts_23, "p_pv"])
        p_pv_24 = float(hist.loc[ts_24, "p_pv"])

        p_load_0 = float(hist.loc[ts_0, "p_load"])
        p_load_1 = float(hist.loc[ts_1, "p_load"])
        p_load_23 = float(hist.loc[ts_23, "p_load"])
        p_load_24 = float(hist.loc[ts_24, "p_load"])

        # Rolling statistics strictly over [T-6h, T] and [T-24h, T]
        slice_6h = hist.loc[origin_ts - pd.Timedelta(hours=6): origin_ts]
        slice_24h = hist.loc[origin_ts - pd.Timedelta(hours=24): origin_ts]

        p_pv_mean_6h = float(slice_6h["p_pv"].mean())
        p_pv_std_6h = float(slice_6h["p_pv"].std(ddof=0))
        p_pv_mean_24h = float(slice_24h["p_pv"].mean())
        p_pv_std_24h = float(slice_24h["p_pv"].std(ddof=0))

        p_load_mean_6h = float(slice_6h["p_load"].mean())
        p_load_std_6h = float(slice_6h["p_load"].std(ddof=0))
        p_load_mean_24h = float(slice_24h["p_load"].mean())
        p_load_std_24h = float(slice_24h["p_load"].std(ddof=0))

        ghi_at_origin = float(hist.loc[ts_0, "ghi"])

        # Forward weather & temporal encodings
        wf = weather_forecast_24h_df.copy()
        if "timestamp" in wf.columns:
            wf["timestamp"] = pd.to_datetime(wf["timestamp"])
            if getattr(wf["timestamp"].dt, "tz", None) is not None:
                wf["timestamp"] = wf["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
            wf["timestamp"] = wf["timestamp"].dt.floor("h")
            wf = wf.sort_values("timestamp").reset_index(drop=True)
            target_timestamps = wf["timestamp"]
        else:
            target_timestamps = pd.date_range(
                start=origin_ts + pd.Timedelta(hours=1),
                periods=self.config.forecast_horizon_hours,
                freq="h",
            )
            wf["timestamp"] = target_timestamps

        if len(wf) != self.config.forecast_horizon_hours:
            raise ValueError(
                f"Weather forecast must have exactly {self.config.forecast_horizon_hours} rows, got {len(wf)}"
            )

        horizons = np.arange(1, self.config.forecast_horizon_hours + 1)
        hours_arr = target_timestamps.dt.hour.to_numpy()
        days_arr = target_timestamps.dt.dayofyear.to_numpy()
        day_of_week = target_timestamps.dt.dayofweek.to_numpy()

        sin_hour = np.sin(2.0 * np.pi * hours_arr / 24.0)
        cos_hour = np.cos(2.0 * np.pi * hours_arr / 24.0)
        sin_day = np.sin(2.0 * np.pi * days_arr / 365.25)
        cos_day = np.cos(2.0 * np.pi * days_arr / 365.25)
        is_weekend = (day_of_week >= 5).astype(float)

        ghi_arr = np.clip(wf["ghi"].to_numpy().astype(float), 0.0, None)
        temp_amb_arr = wf["temp_amb"].to_numpy().astype(float)
        cloud_arr = np.clip(wf["cloud_cover"].to_numpy().astype(float), 0.0, 100.0)

        # Delta GHI: GHI(T+h) - GHI(T+h-1)
        ghi_series_with_t0 = np.concatenate(([ghi_at_origin], ghi_arr))
        delta_ghi = ghi_series_with_t0[1:] - ghi_series_with_t0[:-1]

        features_df = pd.DataFrame({
            "horizon": horizons,
            # PV Origin Lags & Stats
            "p_pv_lag_0": np.full(24, p_pv_0),
            "p_pv_lag_1": np.full(24, p_pv_1),
            "p_pv_lag_23": np.full(24, p_pv_23),
            "p_pv_lag_24": np.full(24, p_pv_24),
            "p_pv_mean_6h": np.full(24, p_pv_mean_6h),
            "p_pv_std_6h": np.full(24, p_pv_std_6h),
            "p_pv_mean_24h": np.full(24, p_pv_mean_24h),
            "p_pv_std_24h": np.full(24, p_pv_std_24h),
            # Load Origin Lags & Stats
            "p_load_lag_0": np.full(24, p_load_0),
            "p_load_lag_1": np.full(24, p_load_1),
            "p_load_lag_23": np.full(24, p_load_23),
            "p_load_lag_24": np.full(24, p_load_24),
            "p_load_mean_6h": np.full(24, p_load_mean_6h),
            "p_load_std_6h": np.full(24, p_load_std_6h),
            "p_load_mean_24h": np.full(24, p_load_mean_24h),
            "p_load_std_24h": np.full(24, p_load_std_24h),
            # Forward Weather
            "ghi_forecast": ghi_arr,
            "delta_ghi": delta_ghi,
            "temp_amb_forecast": temp_amb_arr,
            "cloud_cover_forecast": cloud_arr,
            # Forward Calendar
            "sin_hour": sin_hour,
            "cos_hour": cos_hour,
            "sin_day_of_year": sin_day,
            "cos_day_of_year": cos_day,
            "is_weekend": is_weekend,
            "target_timestamp": target_timestamps.to_numpy(),
        })

        return features_df


def build_training_dataset(
    telemetry_df: pd.DataFrame,
    config: MicrogridConfig = MicrogridConfig(),
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Construct full training dataset across rolling origins in vectorized numpy.

    Generates 24 rows per valid origin T where [T - 48h] and [T + 24h] are available.

    Returns
    -------
    X : pd.DataFrame
        Consolidated feature table.
    y_pv : pd.Series
        Target solar PV power for step T+h.
    y_load : pd.Series
        Target load power for step T+h.
    """
    df = telemetry_df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    else:
        df = df.reset_index().rename(columns={"index": "timestamp"})
    df = df.sort_values("timestamp").reset_index(drop=True)

    n_total = len(df)
    lookback = config.lookback_window_hours # 48
    horizon_max = config.forecast_horizon_hours # 24

    # Valid origin indices: from lookback to (n_total - horizon_max - 1)
    origin_indices = np.arange(lookback, n_total - horizon_max)
    n_origins = len(origin_indices)

    if n_origins <= 0:
        raise ValueError(
            f"Telemetry series too short ({n_total} rows) for lookback={lookback} and horizon={horizon_max}."
        )

    # 1. Precalculate rolling statistics across entire history to avoid per-origin slice loops
    p_pv_series = df["p_pv"]
    p_load_series = df["p_load"]

    pv_m6 = p_pv_series.rolling(window=7, min_periods=7).mean().to_numpy()
    pv_s6 = p_pv_series.rolling(window=7, min_periods=7).std(ddof=0).to_numpy()
    pv_m24 = p_pv_series.rolling(window=25, min_periods=25).mean().to_numpy()
    pv_s24 = p_pv_series.rolling(window=25, min_periods=25).std(ddof=0).to_numpy()

    load_m6 = p_load_series.rolling(window=7, min_periods=7).mean().to_numpy()
    load_s6 = p_load_series.rolling(window=7, min_periods=7).std(ddof=0).to_numpy()
    load_m24 = p_load_series.rolling(window=25, min_periods=25).mean().to_numpy()
    load_s24 = p_load_series.rolling(window=25, min_periods=25).std(ddof=0).to_numpy()

    # 2. Extract origin features (length n_origins)
    p_pv_raw = p_pv_series.to_numpy()
    p_load_raw = p_load_series.to_numpy()
    ghi_raw = df["ghi"].to_numpy()
    temp_raw = df["temp_amb"].to_numpy()
    cloud_raw = df["cloud_cover"].to_numpy()

    orig_pv_lag0 = p_pv_raw[origin_indices]
    orig_pv_lag1 = p_pv_raw[origin_indices - 1]
    orig_pv_lag23 = p_pv_raw[origin_indices - 23]
    orig_pv_lag24 = p_pv_raw[origin_indices - 24]

    orig_pv_m6 = pv_m6[origin_indices]
    orig_pv_s6 = pv_s6[origin_indices]
    orig_pv_m24 = pv_m24[origin_indices]
    orig_pv_s24 = pv_s24[origin_indices]

    orig_load_lag0 = p_load_raw[origin_indices]
    orig_load_lag1 = p_load_raw[origin_indices - 1]
    orig_load_lag23 = p_load_raw[origin_indices - 23]
    orig_load_lag24 = p_load_raw[origin_indices - 24]

    orig_load_m6 = load_m6[origin_indices]
    orig_load_s6 = load_s6[origin_indices]
    orig_load_m24 = load_m24[origin_indices]
    orig_load_s24 = load_s24[origin_indices]

    # Repeat origin features across the 24 horizons
    # Shape: (n_origins * 24,)
    rep_pv_lag0 = np.repeat(orig_pv_lag0, horizon_max)
    rep_pv_lag1 = np.repeat(orig_pv_lag1, horizon_max)
    rep_pv_lag23 = np.repeat(orig_pv_lag23, horizon_max)
    rep_pv_lag24 = np.repeat(orig_pv_lag24, horizon_max)
    rep_pv_m6 = np.repeat(orig_pv_m6, horizon_max)
    rep_pv_s6 = np.repeat(orig_pv_s6, horizon_max)
    rep_pv_m24 = np.repeat(orig_pv_m24, horizon_max)
    rep_pv_s24 = np.repeat(orig_pv_s24, horizon_max)

    rep_load_lag0 = np.repeat(orig_load_lag0, horizon_max)
    rep_load_lag1 = np.repeat(orig_load_lag1, horizon_max)
    rep_load_lag23 = np.repeat(orig_load_lag23, horizon_max)
    rep_load_lag24 = np.repeat(orig_load_lag24, horizon_max)
    rep_load_m6 = np.repeat(orig_load_m6, horizon_max)
    rep_load_s6 = np.repeat(orig_load_s6, horizon_max)
    rep_load_m24 = np.repeat(orig_load_m24, horizon_max)
    rep_load_s24 = np.repeat(orig_load_s24, horizon_max)

    # 3. Horizon target indices: matrix (n_origins, 24)
    # target_idx[i, h-1] = origin_indices[i] + h
    h_offsets = np.arange(1, horizon_max + 1)
    target_idx_matrix = origin_indices[:, None] + h_offsets[None, :]
    flat_target_indices = target_idx_matrix.ravel()

    # Predecessor indices for delta GHI: origin_indices[i] + (h - 1)
    pred_idx_matrix = origin_indices[:, None] + (h_offsets - 1)[None, :]
    flat_pred_indices = pred_idx_matrix.ravel()

    # Weather at target step T+h
    ghi_target = ghi_raw[flat_target_indices]
    ghi_pred = ghi_raw[flat_pred_indices]
    delta_ghi = ghi_target - ghi_pred
    temp_target = temp_raw[flat_target_indices]
    cloud_target = cloud_raw[flat_target_indices]

    # Calendar features at target step T+h
    target_ts = df["timestamp"].iloc[flat_target_indices]
    hours_arr = target_ts.dt.hour.to_numpy()
    days_arr = target_ts.dt.dayofyear.to_numpy()
    day_of_week = target_ts.dt.dayofweek.to_numpy()

    sin_hour = np.sin(2.0 * np.pi * hours_arr / 24.0)
    cos_hour = np.cos(2.0 * np.pi * hours_arr / 24.0)
    sin_day = np.sin(2.0 * np.pi * days_arr / 365.25)
    cos_day = np.cos(2.0 * np.pi * days_arr / 365.25)
    is_weekend = (day_of_week >= 5).astype(float)

    # Relative horizon array [1, 2, ..., 24] tiled
    horizons = np.tile(h_offsets, n_origins)

    # Targets at T+h
    y_pv = p_pv_raw[flat_target_indices]
    y_load = p_load_raw[flat_target_indices]

    X = pd.DataFrame({
        "horizon": horizons,
        # PV
        "p_pv_lag_0": rep_pv_lag0,
        "p_pv_lag_1": rep_pv_lag1,
        "p_pv_lag_23": rep_pv_lag23,
        "p_pv_lag_24": rep_pv_lag24,
        "p_pv_mean_6h": rep_pv_m6,
        "p_pv_std_6h": rep_pv_s6,
        "p_pv_mean_24h": rep_pv_m24,
        "p_pv_std_24h": rep_pv_s24,
        # Load
        "p_load_lag_0": rep_load_lag0,
        "p_load_lag_1": rep_load_lag1,
        "p_load_lag_23": rep_load_lag23,
        "p_load_lag_24": rep_load_lag24,
        "p_load_mean_6h": rep_load_m6,
        "p_load_std_6h": rep_load_s6,
        "p_load_mean_24h": rep_load_m24,
        "p_load_std_24h": rep_load_s24,
        # Weather
        "ghi_forecast": ghi_target,
        "delta_ghi": delta_ghi,
        "temp_amb_forecast": temp_target,
        "cloud_cover_forecast": cloud_target,
        # Calendar
        "sin_hour": sin_hour,
        "cos_hour": cos_hour,
        "sin_day_of_year": sin_day,
        "cos_day_of_year": cos_day,
        "is_weekend": is_weekend,
        # Retain origin and target timestamps for evaluation fold splitting
        "_origin_timestamp": np.repeat(df["timestamp"].iloc[origin_indices].to_numpy(), horizon_max),
        "_target_timestamp": target_ts.to_numpy(),
    })

    return X, pd.Series(y_pv, name="p_pv"), pd.Series(y_load, name="p_load")

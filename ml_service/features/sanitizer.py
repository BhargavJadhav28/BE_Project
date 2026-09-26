"""
Self-Healing Telemetry Sanitizer.

Guarantees clean, gap-free historical inputs before feature extraction:
- Reindexes telemetry to strict hourly frequency ('h').
- Verifies lookback window reaches Forecast Origin T.
- Imputes sensor dropouts <= max_imputable_gap_hours (3h) with physics-aware rules.
- Raises TelemetryGapError on gaps > max_imputable_gap_hours.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


class TelemetryGapError(Exception):
    """Raised when telemetry sensor dropout exceeds the maximum imputable window."""

    pass


class TelemetrySanitizer:
    """Sanitizes raw historical telemetry for microgrid feature engineering."""

    def __init__(
        self,
        lookback_window_hours: int = 48,
        max_imputable_gap_hours: int = 3,
    ) -> None:
        self.lookback_window_hours = lookback_window_hours
        self.max_imputable_gap_hours = max_imputable_gap_hours

    def sanitize(
        self,
        history_df: pd.DataFrame,
        origin: pd.Timestamp | str,
        lookback_hours: Optional[int] = None,
        max_gap_hours: Optional[int] = None,
    ) -> pd.DataFrame:
        """Sanitize and align historical telemetry ending at Forecast Origin T.

        Parameters
        ----------
        history_df : pd.DataFrame
            Historical telemetry containing ['timestamp', 'ghi', 'temp_amb', 'cloud_cover', 'p_pv', 'p_load']
        origin : pd.Timestamp | str
            The forecast origin timestamp T.
        lookback_hours : Optional[int]
            Hours of history required before origin T (default: self.lookback_window_hours).
        max_gap_hours : Optional[int]
            Max consecutive missing hours allowed for interpolation (default: self.max_imputable_gap_hours).

        Returns
        -------
        pd.DataFrame
            Sanitized, gap-free historical DataFrame indexed on strict 1-hour intervals.
        """
        lookback = lookback_hours if lookback_hours is not None else self.lookback_window_hours
        max_gap = max_gap_hours if max_gap_hours is not None else self.max_imputable_gap_hours

        origin_ts = pd.to_datetime(origin)
        if getattr(origin_ts, "tz", None) is not None:
            origin_ts = origin_ts.tz_convert("UTC").tz_localize(None)
        origin_ts = origin_ts.floor("h")

        # 1. Standardize timestamp index to timezone-naive hourly DatetimeIndex
        df = history_df.copy()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            if getattr(df["timestamp"].dt, "tz", None) is not None:
                df["timestamp"] = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
            df["timestamp"] = df["timestamp"].dt.floor("h")
            df = df.set_index("timestamp")
        elif isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is not None:
                df.index = df.index.tz_convert("UTC").tz_localize(None)
            df.index = df.index.floor("h")
        else:
            raise ValueError("history_df must contain a 'timestamp' column or have a DatetimeIndex.")

        df = df[~df.index.duplicated(keep="last")].sort_index()

        # 2. Build expected contiguous hourly index
        start_ts = origin_ts - pd.Timedelta(hours=lookback)
        expected_index = pd.date_range(start=start_ts, end=origin_ts, freq="h")

        # 3. Check boundaries and reindex
        # If the input doesn't reach the start or end by more than max_gap
        if df.empty:
            raise TelemetryGapError("Telemetry history is completely empty.")

        if df.index.max() < origin_ts - pd.Timedelta(hours=max_gap):
            missing_hours = int((origin_ts - df.index.max()).total_seconds() // 3600)
            raise TelemetryGapError(
                f"Telemetry ends {missing_hours}h before origin {origin_ts}, exceeding max gap of {max_gap}h."
            )

        if df.index.min() > start_ts + pd.Timedelta(hours=max_gap):
            missing_hours = int((df.index.min() - start_ts).total_seconds() // 3600)
            raise TelemetryGapError(
                f"Telemetry starts {missing_hours}h after lookback start {start_ts}, exceeding max gap of {max_gap}h."
            )

        reindexed_df = df.reindex(expected_index)

        # 4. Detect consecutive missing streaks
        # A row is considered missing if any key measurement is NaN
        required_cols = [c for c in ["ghi", "temp_amb", "cloud_cover", "p_pv", "p_load"] if c in reindexed_df.columns]
        is_missing = reindexed_df[required_cols].isna().any(axis=1)

        if is_missing.any():
            # Calculate consecutive missing run lengths
            gap_lengths = is_missing.astype(int).groupby((~is_missing).cumsum()).cumsum()
            max_consecutive_gap = int(gap_lengths.max())

            if max_consecutive_gap > max_gap:
                raise TelemetryGapError(
                    f"Consecutive sensor dropout of {max_consecutive_gap} hours exceeds "
                    f"maximum allowable limit of {max_gap} hours."
                )

            # 5. Physics-aware interpolation for gaps <= max_gap
            # Linearly interpolate weather features
            for col in ["ghi", "temp_amb", "cloud_cover", "p_load"]:
                if col in reindexed_df.columns:
                    reindexed_df[col] = reindexed_df[col].interpolate(method="linear", limit=max_gap)
                    reindexed_df[col] = reindexed_df[col].bfill().ffill()

            # For solar PV, zero-fill during nocturnal hours (where GHI <= 0 or night)
            if "p_pv" in reindexed_df.columns:
                is_night = reindexed_df["ghi"] <= 0.0
                reindexed_df.loc[is_night, "p_pv"] = 0.0
                reindexed_df["p_pv"] = reindexed_df["p_pv"].interpolate(method="linear", limit=max_gap)
                reindexed_df["p_pv"] = reindexed_df["p_pv"].bfill().ffill()
                reindexed_df.loc[is_night, "p_pv"] = 0.0

        # Enforce non-negativity and physical bounds on historical sensor measurements and drift
        if "ghi" in reindexed_df.columns:
            reindexed_df["ghi"] = reindexed_df["ghi"].clip(lower=0.0)
        if "p_pv" in reindexed_df.columns:
            reindexed_df["p_pv"] = reindexed_df["p_pv"].clip(lower=0.0)
            if "ghi" in reindexed_df.columns:
                reindexed_df.loc[reindexed_df["ghi"] <= 0.0, "p_pv"] = 0.0
        if "p_load" in reindexed_df.columns:
            reindexed_df["p_load"] = reindexed_df["p_load"].clip(lower=0.0)
        if "cloud_cover" in reindexed_df.columns:
            reindexed_df["cloud_cover"] = reindexed_df["cloud_cover"].clip(lower=0.0, upper=100.0)

        # Final check for remaining NaNs
        if reindexed_df[required_cols].isna().any().any():
            raise TelemetryGapError("Unresolvable missing values remaining after sanitization.")

        reindexed_df = reindexed_df.reset_index().rename(columns={"index": "timestamp"})
        return reindexed_df

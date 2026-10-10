"""
Telemetry Data Ingestion and Source Abstraction.

Provides a unified interface (BaseTelemetrySource) to ingest microgrid
telemetry from synthetic generators or physical CSV/hardware logs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

from ml_service.config import MicrogridConfig
from ml_service.data.synthetic_generator import generate_synthetic_telemetry

REQUIRED_COLUMNS = ["timestamp", "ghi", "temp_amb", "cloud_cover", "p_pv", "p_load"]


class BaseTelemetrySource(ABC):
    """Abstract base class for microgrid telemetry sources."""

    def __init__(self, config: MicrogridConfig = MicrogridConfig()) -> None:
        self.config = config

    @abstractmethod
    def load_telemetry(
        self,
        start_time: Optional[pd.Timestamp | str] = None,
        end_time: Optional[pd.Timestamp | str] = None,
    ) -> pd.DataFrame:
        """Load telemetry within optional temporal bounds.

        Must return a DataFrame with schema:
        ['timestamp', 'ghi', 'temp_amb', 'cloud_cover', 'p_pv', 'p_load']
        """
        pass

    def _validate_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate required columns and ensure timestamp is DatetimeIndex or datetime series."""
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Telemetry missing required columns: {missing}")

        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        if getattr(df["timestamp"].dt, "tz", None) is not None:
            df["timestamp"] = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
        df["timestamp"] = df["timestamp"].dt.floor("h")

        # Enforce float type for numerical metrics
        numeric_cols = ["ghi", "temp_amb", "cloud_cover", "p_pv", "p_load"]
        for col in numeric_cols:
            df[col] = df[col].astype(float)

        return df


def _normalize_bound_timestamp(ts: Optional[pd.Timestamp | str]) -> Optional[pd.Timestamp]:
    if ts is None:
        return None
    t = pd.to_datetime(ts)
    if getattr(t, "tz", None) is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    return t.floor("h")


class SyntheticTelemetrySource(BaseTelemetrySource):
    """Synthetic telemetry provider using deterministic physical models."""

    def __init__(self, config: MicrogridConfig = MicrogridConfig()) -> None:
        super().__init__(config)
        self._cached_df: Optional[pd.DataFrame] = None

    def load_telemetry(
        self,
        start_time: Optional[pd.Timestamp | str] = None,
        end_time: Optional[pd.Timestamp | str] = None,
    ) -> pd.DataFrame:
        if self._cached_df is None:
            self._cached_df = generate_synthetic_telemetry(self.config)

        df = self._cached_df.copy()

        start_ts = _normalize_bound_timestamp(start_time)
        end_ts = _normalize_bound_timestamp(end_time)

        if start_ts is not None:
            df = df[df["timestamp"] >= start_ts]

        if end_ts is not None:
            df = df[df["timestamp"] <= end_ts]

        return df.reset_index(drop=True)


class CSVTelemetrySource(BaseTelemetrySource):
    """Telemetry provider ingesting physical CSV hardware sensor logs."""

    def __init__(
        self,
        config: MicrogridConfig = MicrogridConfig(),
        csv_path: Optional[str | Path] = None,
    ) -> None:
        super().__init__(config)
        self.csv_path = Path(csv_path or config.csv_telemetry_path)

    def load_telemetry(
        self,
        start_time: Optional[pd.Timestamp | str] = None,
        end_time: Optional[pd.Timestamp | str] = None,
    ) -> pd.DataFrame:
        target_path = self.csv_path
        if not target_path.is_absolute() and not target_path.exists():
            candidate = Path(__file__).resolve().parent.parent.parent / target_path
            if candidate.exists():
                target_path = candidate

        if not target_path.exists():
            raise FileNotFoundError(f"Telemetry CSV file not found: {self.csv_path}")

        raw_df = pd.read_csv(target_path)
        df = self._validate_schema(raw_df)

        start_ts = _normalize_bound_timestamp(start_time)
        end_ts = _normalize_bound_timestamp(end_time)

        if start_ts is not None:
            df = df[df["timestamp"] >= start_ts]

        if end_ts is not None:
            df = df[df["timestamp"] <= end_ts]

        return df.sort_values("timestamp").reset_index(drop=True)


def get_telemetry_source(config: MicrogridConfig = MicrogridConfig()) -> BaseTelemetrySource:
    """Factory helper to obtain the configured telemetry source."""
    if config.telemetry_source_type == "synthetic":
        return SyntheticTelemetrySource(config)
    elif config.telemetry_source_type == "csv":
        return CSVTelemetrySource(config)
    else:
        raise ValueError(f"Unsupported telemetry source type: {config.telemetry_source_type}")

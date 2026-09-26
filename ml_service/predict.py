"""
Microgrid 24-Hour Rolling Forecaster and CLI Interface.

Provides dual-mode consumption:
1. In-process Python class (MicrogridForecaster) delivering < 25ms 24-step inference.
2. CLI runner for decoupled microgrid controller invocation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

import pandas as pd

# Allow execution both as module and directly as script
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_service.config import MicrogridConfig
from ml_service.features.pipeline import FeaturePipeline
from ml_service.features.sanitizer import TelemetrySanitizer
from ml_service.models.load_model import LoadForecaster
from ml_service.models.pv_model import PVForecaster
from ml_service.postprocessing.boundary_enforcer import PhysicalBoundaryEnforcer


class MicrogridForecaster:
    """In-process production forecasting engine for Solar PV and Load Demand."""

    def __init__(
        self,
        config: MicrogridConfig = MicrogridConfig(),
        artifacts_dir: Optional[str | Path] = None,
    ) -> None:
        self.config = config
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else config.get_artifacts_dir_path()

        self.sanitizer = TelemetrySanitizer(
            lookback_window_hours=config.lookback_window_hours,
            max_imputable_gap_hours=config.max_imputable_gap_hours,
        )
        self.pipeline = FeaturePipeline(config=config)
        self.enforcer = PhysicalBoundaryEnforcer(config=config)

        self.pv_model = PVForecaster(config=config)
        self.load_model = LoadForecaster(config=config)

        self._load_artifacts()

    def _load_artifacts(self) -> None:
        """Load serialized model weights and verify manifest."""
        pv_path = self.artifacts_dir / self.config.pv_model_filename
        load_path = self.artifacts_dir / self.config.load_model_filename

        if not pv_path.exists() or not load_path.exists():
            raise FileNotFoundError(
                f"Model artifacts not found in {self.artifacts_dir}. "
                "Please run 'python train.py' to generate trained checkpoints first."
            )

        self.pv_model.load(pv_path)
        self.load_model.load(load_path)

        manifest_path = self.artifacts_dir / self.config.manifest_filename
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {}

    def predict_next_24h(
        self,
        current_timestamp: pd.Timestamp | str,
        recent_history_df: pd.DataFrame,
        weather_forecast_24h_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Generate 24-hour forward predictions for Solar PV generation and Load Demand.

        Parameters
        ----------
        current_timestamp : pd.Timestamp | str
            Forecast origin timestamp T.
        recent_history_df : pd.DataFrame
            Sensor telemetry covering at least [T - 48h, T].
        weather_forecast_24h_df : pd.DataFrame
            Weather predictions covering [T + 1h, T + 24h].

        Returns
        -------
        dict
            {
                "timestamps": ["2026-03-01T13:00:00", ... 24 ISO strings],
                "p_pv_forecast": [0.0, 12.4, ... 24 non-negative floats in kW],
                "p_load_forecast": [18.2, 19.5, ... 24 non-negative floats in kW],
                "metadata": {
                    "origin": "2026-03-01T12:00:00",
                    "execution_time_ms": 14.2
                }
            }
        """
        t_start = time.perf_counter()
        origin_ts = pd.to_datetime(current_timestamp)
        if getattr(origin_ts, "tz", None) is not None:
            origin_ts = origin_ts.tz_convert("UTC").tz_localize(None)
        origin_ts = origin_ts.floor("h")

        # 1. Sanitize recent history
        sanitized_history = self.sanitizer.sanitize(
            history_df=recent_history_df,
            origin=origin_ts,
            lookback_hours=self.config.lookback_window_hours,
            max_gap_hours=self.config.max_imputable_gap_hours,
        )

        # 2. Extract origin-anchored 24-step features
        features_df = self.pipeline.extract_features_for_origin(
            origin=origin_ts,
            sanitized_history_df=sanitized_history,
            weather_forecast_24h_df=weather_forecast_24h_df,
        )

        # 3. Model regression inference
        raw_pv = self.pv_model.predict(features_df)
        raw_load = self.load_model.predict(features_df)

        # 4. Physical boundary enforcement
        clean_pv, clean_load = self.enforcer.enforce(
            raw_p_pv=raw_pv,
            raw_p_load=raw_load,
            ghi=features_df["ghi_forecast"].to_numpy(),
        )

        # 5. Format payload
        target_timestamps = [pd.to_datetime(ts).isoformat() for ts in features_df["target_timestamp"]]
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "timestamps": target_timestamps,
            "p_pv_forecast": [float(x) for x in clean_pv],
            "p_load_forecast": [float(x) for x in clean_load],
            "metadata": {
                "origin": origin_ts.isoformat(),
                "execution_time_ms": round(latency_ms, 2),
            },
        }


def run_sample_prediction() -> Dict[str, Any]:
    """Execute a demonstration 24-hour prediction using synthetic data."""
    from ml_service.data.synthetic_generator import generate_synthetic_telemetry

    config = MicrogridConfig()
    print("Generating synthetic benchmark telemetry...")
    full_df = generate_synthetic_telemetry(config)

    # Pick an origin: June 15 at 12:00 PM (Summer day)
    origin = pd.Timestamp("2026-06-15 12:00:00")
    history_start = origin - pd.Timedelta(hours=48)
    forecast_end = origin + pd.Timedelta(hours=24)

    history_df = full_df[(full_df["timestamp"] >= history_start) & (full_df["timestamp"] <= origin)].copy()
    future_df = full_df[(full_df["timestamp"] > origin) & (full_df["timestamp"] <= forecast_end)].copy()
    weather_df = future_df[["timestamp", "ghi", "temp_amb", "cloud_cover"]].copy()

    forecaster = MicrogridForecaster(config)
    result = forecaster.predict_next_24h(origin, history_df, weather_df)

    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="24-Hour Solar PV & Load Demand Forecaster")
    parser.add_argument("--origin", type=str, help="Forecast origin ISO timestamp (e.g. 2026-06-15T12:00:00)")
    parser.add_argument("--history-path", type=str, help="Path to historical sensor CSV (at least past 48h)")
    parser.add_argument("--weather-path", type=str, help="Path to 24h weather forecast CSV")
    parser.add_argument("--output", type=str, help="Path to write JSON forecast output")
    parser.add_argument("--sample", action="store_true", help="Run a demonstration prediction using synthetic telemetry")

    args = parser.parse_args()

    if args.sample:
        run_sample_prediction()
        return

    if not (args.origin and args.history_path and args.weather_path):
        parser.print_help()
        sys.exit(1)

    origin = pd.to_datetime(args.origin)
    history_df = pd.read_csv(args.history_path)
    weather_df = pd.read_csv(args.weather_path)

    forecaster = MicrogridForecaster()
    result = forecaster.predict_next_24h(origin, history_df, weather_df)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Forecast written to {out_path}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

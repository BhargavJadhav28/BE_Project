"""
4-Season Rolling-Origin Training and Evaluation Pipeline.

Trains LightGBM regressors for Solar PV and Load Demand:
- Evaluates across 4 chronological seasonal folds (Spring, Summer, Autumn, Winter)
- Daylight-masked, capacity-normalized evaluation for Solar PV (nMAE <= 5.0%, R2 >= 0.85)
- Capacity-normalized evaluation for Load Demand (nMAE <= 6.0%, R2 >= 0.85)
- Serializes final production models and manifest.json to artifacts/
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

# Allow execution both as module and directly as script
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_service.config import MicrogridConfig
from ml_service.data.loader import get_telemetry_source
from ml_service.features.pipeline import (
    LOAD_FEATURE_NAMES,
    PV_FEATURE_NAMES,
    build_training_dataset,
)
from ml_service.models.load_model import LoadForecaster
from ml_service.models.pv_model import PVForecaster
from ml_service.postprocessing.boundary_enforcer import PhysicalBoundaryEnforcer


def compute_metrics(
    y_true_pv: np.ndarray,
    y_pred_pv: np.ndarray,
    ghi: np.ndarray,
    y_true_load: np.ndarray,
    y_pred_load: np.ndarray,
    config: MicrogridConfig,
) -> Dict[str, float]:
    """Compute capacity-normalized MAE and R2 scores."""
    # PV Daylight Masked (GHI > 0)
    daylight_mask = ghi > 0.0
    if np.sum(daylight_mask) > 0:
        pv_true_day = y_true_pv[daylight_mask]
        pv_pred_day = y_pred_pv[daylight_mask]
        pv_daylight_mae = float(np.mean(np.abs(pv_true_day - pv_pred_day)))
        pv_daylight_nmae = float(pv_daylight_mae / config.pv_peak_kw)
        pv_daylight_r2 = float(r2_score(pv_true_day, pv_pred_day))
    else:
        pv_daylight_nmae = 0.0
        pv_daylight_r2 = 1.0

    # Load Demand (All Hours)
    load_mae = float(np.mean(np.abs(y_true_load - y_pred_load)))
    load_nmae = float(load_mae / config.load_peak_kw)
    load_r2 = float(r2_score(y_true_load, y_pred_load))

    return {
        "pv_daylight_nmae": round(pv_daylight_nmae, 4),
        "pv_daylight_nmae_pct": round(pv_daylight_nmae * 100.0, 2),
        "pv_daylight_r2": round(pv_daylight_r2, 4),
        "load_nmae": round(load_nmae, 4),
        "load_nmae_pct": round(load_nmae * 100.0, 2),
        "load_r2": round(load_r2, 4),
    }


def run_training(config: MicrogridConfig = MicrogridConfig()) -> Dict[str, Any]:
    """Execute the full 4-season cross-validation and production training pipeline."""
    start_time = time.time()
    print("=" * 70)
    print("Starting Microgrid 24-Hour Forecasting Training Pipeline")
    print(f"Asset Ratings: PV Peak={config.pv_peak_kw}kW, Load Peak={config.load_peak_kw}kW")
    print("=" * 70)

    # 1. Load Telemetry
    telemetry_source = get_telemetry_source(config)
    print(f"Loading telemetry using {type(telemetry_source).__name__}...")
    telemetry_df = telemetry_source.load_telemetry()
    print(f"Loaded {len(telemetry_df)} hourly telemetry records.")

    # 2. Build Origin-Anchored Training Dataset
    print("Building origin-anchored horizon-conditioned tabular dataset...")
    t_data_0 = time.time()
    X, y_pv, y_load = build_training_dataset(telemetry_df, config)
    t_data_build = time.time() - t_data_0
    print(f"Dataset constructed: {len(X)} rows across 24 horizons ({t_data_build:.2f}s).")

    # 3. 4-Season Rolling-Origin Validation
    # Test windows: 7 consecutive days (168 origins) per season
    seasonal_folds = [
        ("spring", "2026-03-15 00:00:00", "2026-03-21 23:00:00"),
        ("summer", "2026-06-15 00:00:00", "2026-06-21 23:00:00"),
        ("autumn", "2026-09-15 00:00:00", "2026-09-21 23:00:00"),
        ("winter", "2026-12-15 00:00:00", "2026-12-21 23:00:00"),
    ]

    boundary_enforcer = PhysicalBoundaryEnforcer(config)
    fold_results = {}

    print("\nExecuting 4-Season Rolling-Origin Validation:")
    print("-" * 70)

    for season_name, fold_start_str, fold_end_str in seasonal_folds:
        fold_start = pd.to_datetime(fold_start_str)
        fold_end = pd.to_datetime(fold_end_str)

        # Prevent forward target leakage into the test evaluation window
        train_mask = X["_target_timestamp"] < fold_start
        test_mask = (X["_origin_timestamp"] >= fold_start) & (X["_origin_timestamp"] <= fold_end)

        X_train, y_train_pv, y_train_load = X[train_mask], y_pv[train_mask], y_load[train_mask]
        X_test, y_test_pv, y_test_load = X[test_mask], y_pv[test_mask], y_load[test_mask]

        if len(X_train) == 0 or len(X_test) == 0:
            print(f"Skipping fold {season_name}: insufficient historical samples prior to {fold_start}.")
            continue

        # Fit PV and Load models strictly on past origins
        fold_pv_model = PVForecaster(config).fit(X_train, y_train_pv)
        fold_load_model = LoadForecaster(config).fit(X_train, y_train_load)

        # Raw predictions
        raw_pred_pv = fold_pv_model.predict(X_test)
        raw_pred_load = fold_load_model.predict(X_test)

        # Physical boundary enforcement
        clean_pred_pv, clean_pred_load = boundary_enforcer.enforce(
            raw_pred_pv, raw_pred_load, X_test["ghi_forecast"].to_numpy()
        )

        metrics = compute_metrics(
            y_test_pv.to_numpy(),
            clean_pred_pv,
            X_test["ghi_forecast"].to_numpy(),
            y_test_load.to_numpy(),
            clean_pred_load,
            config,
        )
        fold_results[season_name] = metrics
        print(
            f"Fold [{season_name.upper():<6}]: "
            f"PV Daylight nMAE={metrics['pv_daylight_nmae_pct']:.2f}% (R2={metrics['pv_daylight_r2']:.3f}) | "
            f"Load nMAE={metrics['load_nmae_pct']:.2f}% (R2={metrics['load_r2']:.3f})"
        )

    # 4. Fit Production Models on Full Telemetry
    print("-" * 70)
    print("Training final production models on full 1-year telemetry...")
    t_train_0 = time.time()
    final_pv_model = PVForecaster(config).fit(X, y_pv)
    final_load_model = LoadForecaster(config).fit(X, y_load)
    train_duration = time.time() - t_train_0
    print(f"Production models trained in {train_duration:.2f}s.")

    # In-sample evaluation on full dataset
    raw_full_pv = final_pv_model.predict(X)
    raw_full_load = final_load_model.predict(X)
    clean_full_pv, clean_full_load = boundary_enforcer.enforce(
        raw_full_pv, raw_full_load, X["ghi_forecast"].to_numpy()
    )
    full_metrics = compute_metrics(
        y_pv.to_numpy(),
        clean_full_pv,
        X["ghi_forecast"].to_numpy(),
        y_load.to_numpy(),
        clean_full_load,
        config,
    )

    # Average cross-validation scores
    avg_cv_metrics = {}
    if fold_results:
        for k in fold_results[next(iter(fold_results))]:
            vals = [fold_results[s][k] for s in fold_results]
            avg_cv_metrics[f"avg_{k}"] = round(float(np.mean(vals)), 4)

    # Validate against Quality Acceptance Targets
    pv_target_met = (
        avg_cv_metrics.get("avg_pv_daylight_nmae", full_metrics["pv_daylight_nmae"])
        <= config.pv_daylight_nmae_target
    )
    load_target_met = (
        avg_cv_metrics.get("avg_load_nmae", full_metrics["load_nmae"])
        <= config.load_nmae_target
    )
    r2_target_met = (
        avg_cv_metrics.get("avg_pv_daylight_r2", full_metrics["pv_daylight_r2"])
        >= config.r2_score_target
        and avg_cv_metrics.get("avg_load_r2", full_metrics["load_r2"])
        >= config.r2_score_target
    )
    all_targets_passed = bool(pv_target_met and load_target_met and r2_target_met)

    print("\nValidation Summary:")
    print(f"• PV Daylight nMAE Target (<= {config.pv_daylight_nmae_target*100:.1f}%): "
          f"{avg_cv_metrics.get('avg_pv_daylight_nmae_pct', full_metrics['pv_daylight_nmae_pct'])}% -> {'PASSED' if pv_target_met else 'FAILED'}")
    print(f"• Load nMAE Target (<= {config.load_nmae_target*100:.1f}%): "
          f"{avg_cv_metrics.get('avg_load_nmae_pct', full_metrics['load_nmae_pct'])}% -> {'PASSED' if load_target_met else 'FAILED'}")
    print(f"• R2 Score Target (>= {config.r2_score_target}): "
          f"PV={avg_cv_metrics.get('avg_pv_daylight_r2', full_metrics['pv_daylight_r2'])}, "
          f"Load={avg_cv_metrics.get('avg_load_r2', full_metrics['load_r2'])} -> {'PASSED' if r2_target_met else 'FAILED'}")

    # 5. Serialize Artifacts
    artifacts_dir = config.get_artifacts_dir_path()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    pv_path = config.get_pv_model_path()
    load_path = config.get_load_model_path()
    manifest_path = config.get_manifest_path()

    print(f"\nSerializing models to {artifacts_dir}...")
    final_pv_model.save(pv_path)
    final_load_model.save(load_path)

    manifest_data = {
        "model_version": "1.0.0",
        "trained_at": datetime.now().isoformat(),
        "config": {
            "pv_peak_kw": config.pv_peak_kw,
            "load_peak_kw": config.load_peak_kw,
            "base_load_kw": config.base_load_kw,
            "forecast_horizon_hours": config.forecast_horizon_hours,
            "lookback_window_hours": config.lookback_window_hours,
            "n_estimators": config.n_estimators,
            "learning_rate": config.learning_rate,
            "num_leaves": config.num_leaves,
            "max_depth": config.max_depth,
            "random_seed": config.random_seed,
        },
        "feature_schema": {
            "pv_features": PV_FEATURE_NAMES,
            "load_features": LOAD_FEATURE_NAMES,
        },
        "seasonal_validation_metrics": fold_results,
        "aggregate_cv_metrics": avg_cv_metrics,
        "full_dataset_metrics": full_metrics,
        "quality_targets_met": all_targets_passed,
        "total_training_pipeline_seconds": round(time.time() - start_time, 2),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"Saved artifacts:")
    print(f"  - {pv_path}")
    print(f"  - {load_path}")
    print(f"  - {manifest_path}")
    print(f"Training pipeline finished in {time.time() - start_time:.2f}s.")
    print("=" * 70)

    return manifest_data


if __name__ == "__main__":
    run_training()

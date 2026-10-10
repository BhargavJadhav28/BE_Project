"""
Root runner for microgrid training pipeline.
Delegates to ml_service.train.
"""

import sys
from ml_service.train import run_training
from ml_service.config import MicrogridConfig

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train Microgrid Forecasting Models.")
    parser.add_argument(
        "--source",
        choices=["synthetic", "csv"],
        default="csv",
        help="Telemetry source: 'csv' (default) or 'synthetic'.",
    )
    parser.add_argument(
        "--csv-path",
        default="data/raw_telemetry.csv",
        help="Path to telemetry CSV file if --source csv is selected.",
    )
    args = parser.parse_args()
    config = MicrogridConfig(
        telemetry_source_type=args.source,
        csv_telemetry_path=args.csv_path,
    )
    run_training(config)

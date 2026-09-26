"""
Abstract Base Forecaster Interface.

Defines the required methods for all microgrid horizon-conditioned regressors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig


class BaseForecaster(ABC):
    """Abstract base forecaster defining fit, predict, save, and load contracts."""

    def __init__(self, config: MicrogridConfig = MicrogridConfig()) -> None:
        self.config = config
        self.model = None
        self.feature_names: list[str] = []

    @abstractmethod
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series | np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series | np.ndarray] = None,
    ) -> BaseForecaster:
        """Fit the regressor on the provided feature matrix and target series."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate regression predictions from the input feature matrix."""
        pass

    def save(self, file_path: str | Path) -> None:
        """Serialize model weights and metadata to disk."""
        target_path = Path(file_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "feature_names": self.feature_names,
                "config": self.config,
            },
            target_path,
        )

    def load(self, file_path: str | Path) -> BaseForecaster:
        """Load serialized model weights and metadata from disk."""
        target_path = Path(file_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {target_path}")

        payload = joblib.load(target_path)
        self.model = payload["model"]
        self.feature_names = payload.get("feature_names", [])
        return self

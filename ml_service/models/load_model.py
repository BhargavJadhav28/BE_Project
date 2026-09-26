"""
Horizon-Conditioned Load Demand Forecaster.

LightGBM regressor predicting 24h forward microgrid electrical load demand
conditioned on horizon index h, historical lags, and temperature.
"""

from __future__ import annotations

from typing import Optional

from lightgbm import LGBMRegressor, early_stopping
import numpy as np
import pandas as pd

from ml_service.config import MicrogridConfig
from ml_service.features.pipeline import LOAD_FEATURE_NAMES
from ml_service.models.base import BaseForecaster


class LoadForecaster(BaseForecaster):
    """Origin-anchored horizon-conditioned Load demand regressor."""

    def __init__(self, config: MicrogridConfig = MicrogridConfig()) -> None:
        super().__init__(config)
        self.feature_names = list(LOAD_FEATURE_NAMES)
        self.model = LGBMRegressor(
            objective="regression",
            metric="rmse",
            n_estimators=self.config.n_estimators,
            learning_rate=self.config.learning_rate,
            num_leaves=self.config.num_leaves,
            max_depth=self.config.max_depth,
            random_state=self.config.random_seed,
            n_jobs=self.config.n_jobs,
            verbose=-1,
        )

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series | np.ndarray,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series | np.ndarray] = None,
    ) -> LoadForecaster:
        """Fit the LightGBM Load model on training data."""
        X_feat = X[self.feature_names]

        if X_val is not None and y_val is not None:
            X_val_feat = X_val[self.feature_names]
            callbacks = [early_stopping(stopping_rounds=self.config.early_stopping_rounds, verbose=False)]
            self.model.fit(
                X_feat,
                y,
                eval_set=[(X_val_feat, y_val)],
                callbacks=callbacks,
            )
        else:
            self.model.fit(X_feat, y)

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict raw electrical load demand (kW)."""
        if self.model is None:
            raise RuntimeError("Model has not been trained or loaded.")
        X_feat = X[self.feature_names]
        return self.model.predict(X_feat)

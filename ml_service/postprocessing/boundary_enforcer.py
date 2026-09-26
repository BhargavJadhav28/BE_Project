"""
Physical Post-Processing and Boundary Enforcer.

Enforces physical microgrid limits post-inference:
1. Hard Nocturnal Zeroing: If GHI <= 0.0 W/m^2, sets solar PV prediction to 0.0 kW.
2. Inverter Power Clipping: Clips solar PV to [0.0, pv_peak_kw].
3. Load Demand Bounding: Clips load demand to [0.0, 1.2 * load_peak_kw].
"""

from __future__ import annotations

import numpy as np

from ml_service.config import MicrogridConfig


class PhysicalBoundaryEnforcer:
    """Enforces deterministic physical boundary conditions on raw ML predictions."""

    def __init__(self, config: MicrogridConfig = MicrogridConfig()) -> None:
        self.config = config

    def enforce_pv_boundaries(
        self,
        raw_p_pv: np.ndarray | list[float],
        ghi: np.ndarray | list[float],
    ) -> np.ndarray:
        """Apply nocturnal zeroing and inverter capacity clipping on solar PV predictions.

        Parameters
        ----------
        raw_p_pv : np.ndarray or list of floats
            Raw regression predictions for P_pv (kW).
        ghi : np.ndarray or list of floats
            Forecasted Global Horizontal Irradiance (W/m^2).

        Returns
        -------
        np.ndarray
            Physically bounded P_pv predictions.
        """
        pv_arr = np.nan_to_num(np.asarray(raw_p_pv, dtype=float), nan=0.0, posinf=self.config.pv_peak_kw, neginf=0.0)
        ghi_arr = np.nan_to_num(np.asarray(ghi, dtype=float), nan=0.0, posinf=1000.0, neginf=0.0)

        # 1. Hard nocturnal zeroing when GHI is 0 or negative
        pv_arr[ghi_arr <= 0.0] = 0.0

        # 2. Hard clipping to [0.0, pv_peak_kw]
        pv_arr = np.clip(pv_arr, 0.0, self.config.pv_peak_kw)

        return np.round(pv_arr, 3)

    def enforce_load_boundaries(
        self,
        raw_p_load: np.ndarray | list[float],
    ) -> np.ndarray:
        """Apply non-negativity and maximum operational bounds on load demand predictions.

        Parameters
        ----------
        raw_p_load : np.ndarray or list of floats
            Raw regression predictions for P_load (kW).

        Returns
        -------
        np.ndarray
            Physically bounded P_load predictions.
        """
        max_limit = 1.2 * self.config.load_peak_kw
        load_arr = np.nan_to_num(
            np.asarray(raw_p_load, dtype=float),
            nan=self.config.base_load_kw,
            posinf=max_limit,
            neginf=0.0,
        )
        load_arr = np.clip(load_arr, 0.0, max_limit)

        return np.round(load_arr, 3)

    def enforce(
        self,
        raw_p_pv: np.ndarray | list[float],
        raw_p_load: np.ndarray | list[float],
        ghi: np.ndarray | list[float],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply boundary enforcement across both generation and load predictions."""
        clean_pv = self.enforce_pv_boundaries(raw_p_pv, ghi)
        clean_load = self.enforce_load_boundaries(raw_p_load)
        return clean_pv, clean_load

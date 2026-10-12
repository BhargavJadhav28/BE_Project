# Helios Forecasting Models: Parameter-Level Input and Output Flowcharts

This document describes all original parameters for the Helios machine learning models.
The language follows the ASD-STE100 specification.
All sentences are short, active, and direct.

---

## 1. Inference / Forecasting Parameter Flowchart

This flowchart shows all input parameters, feature parameters, models, and output parameters.

```mermaid
flowchart TD
    subgraph RAW_INPUTS ["1. Original Input Parameters"]
        subgraph TIME_ORIGIN ["Origin Reference"]
            P_ORIGIN["origin: UTC ISO 8601 Timestamp (T)"]
        end

        subgraph HIST_SERIES ["Telemetry History: [T - 48h, T] (49 Hourly Samples)"]
            P_HIST_GHI["ghi: Past Solar Irradiance (W/m2)"]
            P_HIST_TEMP["temp_amb: Past Ambient Temperature (deg C)"]
            P_HIST_CLOUD["cloud_cover: Past Cloud Cover (percent)"]
            P_HIST_PV["p_pv: Past Solar Generation (kW)"]
            P_HIST_LOAD["p_load: Past Facility Demand (kW)"]
        end

        subgraph FWD_WEATHER ["Weather Forecast: [T + 1h, T + 24h] (24 Hourly Steps)"]
            P_FWD_GHI["ghi_forecast: Future Irradiance (W/m2)"]
            P_FWD_TEMP["temp_amb_forecast: Future Temperature (deg C)"]
            P_FWD_CLOUD["cloud_cover_forecast: Future Cloud Cover (percent)"]
        end
    end

    subgraph FEAT_MATRIX ["2. Engineered Model Features"]
        subgraph PV_FEATURES ["Solar PV Features (18 Parameters per Horizon Step)"]
            F_PV_HORIZON["horizon: Step Index (1 to 24)"]
            F_PV_LAGS["p_pv_lag_0, p_pv_lag_1, p_pv_lag_23, p_pv_lag_24 (kW)"]
            F_PV_STATS["p_pv_mean_6h, p_pv_std_6h, p_pv_mean_24h, p_pv_std_24h (kW)"]
            F_PV_WEATHER["ghi_forecast, delta_ghi, temp_amb_forecast, cloud_cover_forecast"]
            F_PV_CAL["sin_hour, cos_hour, sin_day_of_year, cos_day_of_year, is_weekend"]
        end

        subgraph LOAD_FEATURES ["Load Demand Features (15 Parameters per Horizon Step)"]
            F_LD_HORIZON["horizon: Step Index (1 to 24)"]
            F_LD_LAGS["p_load_lag_0, p_load_lag_1, p_load_lag_23, p_load_lag_24 (kW)"]
            F_LD_STATS["p_load_mean_6h, p_load_std_6h, p_load_mean_24h, p_load_std_24h (kW)"]
            F_LD_WEATHER["temp_amb_forecast (HVAC Thermal Driver)"]
            F_LD_CAL["sin_hour, cos_hour, sin_day_of_year, cos_day_of_year, is_weekend"]
        end
    end

    subgraph MODELS ["3. Trained Model Regressors"]
        M_PV["Solar PV Forecaster: LightGBM Model (pv_model.joblib)"]
        M_LD["Load Demand Forecaster: LightGBM Model (load_model.joblib)"]
    end

    subgraph RAW_PRED ["4. Raw Model Predictions"]
        R_PV["p_pv_raw: Unconstrained Solar Power (24 floats, kW)"]
        R_LD["p_load_raw: Unconstrained Load Demand (24 floats, kW)"]
    end

    subgraph BOUNDARY_GUARD ["5. Physical Post-Processing Rules"]
        GUARD_NAN["Rule 1: Replace NaN Values with Baseload Defaults"]
        GUARD_NIGHT["Rule 2: Nocturnal Zero (If GHI <= 0.0 then p_pv = 0.0 kW)"]
        GUARD_PV_CLIP["Rule 3: Inverter Clip: p_pv in [0.0, 50.0] kW"]
        GUARD_LD_CLIP["Rule 4: Load Envelope Clip: p_load in [0.0, 54.0] kW"]
    end

    subgraph FINAL_OUTPUTS ["6. Final Model Output Parameters"]
        OUT_TIMESTAMPS["timestamps: Sequence of 24 ISO 8601 UTC Timestamps"]
        OUT_PV["p_pv_forecast: 24 Hourly Solar Generation Values (kW)"]
        OUT_LOAD["p_load_forecast: 24 Hourly Load Demand Values (kW)"]
        OUT_NET["p_net_forecast: 24 Net Power Values (P_net = P_pv - P_load)"]
        OUT_META["execution_time_ms: Inference Latency (Under 25 ms)"]
    end

    %% Wiring Inputs to Features
    P_ORIGIN --> FEAT_MATRIX
    HIST_SERIES --> FEAT_MATRIX
    FWD_WEATHER --> FEAT_MATRIX

    %% Wiring Features to Models
    PV_FEATURES --> M_PV
    LOAD_FEATURES --> M_LD

    %% Wiring Models to Raw Predictions
    M_PV --> R_PV
    M_LD --> R_LD

    %% Wiring to Boundary Guard
    R_PV --> BOUNDARY_GUARD
    R_LD --> BOUNDARY_GUARD
    P_FWD_GHI --> GUARD_NIGHT

    %% Wiring Guard to Final Outputs
    BOUNDARY_GUARD --> OUT_TIMESTAMPS
    BOUNDARY_GUARD --> OUT_PV
    BOUNDARY_GUARD --> OUT_LOAD
    OUT_PV --> OUT_NET
    OUT_LOAD --> OUT_NET
    BOUNDARY_GUARD --> OUT_META
```

---

## 2. Model Training Parameter Flowchart

This flowchart shows all input parameters, hyperparameters, targets, and output artifacts for the training phase.

```mermaid
flowchart TD
    subgraph TR_INPUT_PARAMS ["1. Training Input Parameters"]
        subgraph TR_DATA ["Full-Year Historical Telemetry (8,760 Rows)"]
            T_TIMESTAMP["timestamp: UTC Sampling Time"]
            T_GHI["ghi: Observed Solar Irradiance (W/m2)"]
            T_TEMP["temp_amb: Observed Temperature (deg C)"]
            T_CLOUD["cloud_cover: Observed Cloud Fraction (percent)"]
            T_PV["p_pv: Observed Active Solar Generation (kW)"]
            T_LOAD["p_load: Observed Electrical Load Demand (kW)"]
        end

        subgraph TR_CONFIG ["System Sizing and Window Parameters"]
            C_PV_PEAK["pv_peak_kw: 50.0 kW Inverter Rating"]
            C_LOAD_PEAK["load_peak_kw: 45.0 kW Peak Facility Demand"]
            C_BASE_LOAD["base_load_kw: 10.0 kW Baseline Demand"]
            C_LOOKBACK["lookback_window_hours: 48 Hours"]
            C_HORIZON["forecast_horizon_hours: 24 Hours"]
        end

        subgraph TR_HYPER ["LightGBM Hyperparameters"]
            H_TREES["n_estimators: 150 Boosting Rounds"]
            H_RATE["learning_rate: 0.05 Step Size"]
            H_LEAVES["num_leaves: 31 Max Leaves per Tree"]
            H_DEPTH["max_depth: 6 Levels"]
            H_STOP["early_stopping_rounds: 15 Rounds"]
            H_SEED["random_state: 42 Seed"]
        end

        subgraph TR_TARGETS ["Ground Truth Training Targets"]
            Y_PV["y_pv: True Solar Power at Horizon Step T + h (kW)"]
            Y_LOAD["y_load: True Load Demand at Horizon Step T + h (kW)"]
        end
    end

    subgraph TR_PROCESS ["2. Training and Validation Engine"]
        TR_BUILD["Feature Dataset Generator: 8,688 Origins x 24 Horizons"]
        TR_SPLIT["4-Season Rolling Validation: Spring, Summer, Autumn, Winter"]
        TR_FIT_PV["Fit PV Model: Train LightGBM on 18 Solar Features"]
        TR_FIT_LD["Fit Load Model: Train LightGBM on 15 Load Features"]
        TR_BUILD --> TR_SPLIT
        TR_SPLIT --> TR_FIT_PV
        TR_SPLIT --> TR_FIT_LD
    end

    subgraph TR_OUTPUT_PARAMS ["3. Training Output Artifacts & Metrics"]
        subgraph ARTIFACTS ["Model Binary Files"]
            FILE_PV["pv_model.joblib: Serialized PV Regressor (~350 KB)"]
            FILE_LOAD["load_model.joblib: Serialized Load Regressor (~400 KB)"]
            FILE_MANIFEST["manifest.json: Training Configuration and Metrics"]
        end

        subgraph VALIDATION_METRICS ["Quality Verification Metrics"]
            M_PV_NMAE["pv_daylight_nmae: 0.30 percent (SLA Target <= 5.0 percent)"]
            M_PV_R2["pv_daylight_r2: 0.9996 (SLA Target >= 0.85)"]
            M_LD_NMAE["load_nmae: 3.09 percent (SLA Target <= 6.0 percent)"]
            M_LD_R2["load_r2: 0.9259 (SLA Target >= 0.85)"]
        end
    end

    %% Connections
    TR_DATA --> TR_BUILD
    TR_CONFIG --> TR_BUILD
    TR_TARGETS --> TR_BUILD
    TR_HYPER --> TR_FIT_PV
    TR_HYPER --> TR_FIT_LD

    TR_FIT_PV --> FILE_PV
    TR_FIT_LD --> FILE_LOAD
    TR_FIT_PV --> VALIDATION_METRICS
    TR_FIT_LD --> VALIDATION_METRICS
    VALIDATION_METRICS --> FILE_MANIFEST
```

---

## 3. Original Parameter Reference Tables

### 3.1 Inference Input Parameters

| Parameter Name | Data Type | Engineering Unit | Physical Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `origin` | String / Datetime | UTC ISO 8601 | Whole hour | Reference timestamp $T$ anchoring the forecast. |
| `ghi` (history) | Float Array | W/m2 | $\ge 0.0$ | Observed solar irradiance from pyranometer ($[T-48\text{h}, T]$). |
| `temp_amb` (history) | Float Array | deg C | $[-20.0, 55.0]$ | Observed dry-bulb ambient temperature ($[T-48\text{h}, T]$). |
| `cloud_cover` (history) | Float Array | percent | $[0.0, 100.0]$ | Observed cloud fraction percentage ($[T-48\text{h}, T]$). |
| `p_pv` (history) | Float Array | kW | $[0.0, 50.0]$ | Observed solar PV inverter active power ($[T-48\text{h}, T]$). |
| `p_load` (history) | Float Array | kW | $[0.0, 54.0]$ | Observed facility load demand power ($[T-48\text{h}, T]$). |
| `ghi_forecast` | Float Array | W/m2 | $\ge 0.0$ | Forecasted solar irradiance for 24 future steps ($[T+1\text{h}, T+24\text{h}]$). |
| `temp_amb_forecast` | Float Array | deg C | $[-20.0, 55.0]$ | Forecasted ambient temperature for 24 future steps ($[T+1\text{h}, T+24\text{h}]$). |
| `cloud_cover_forecast` | Float Array | percent | $[0.0, 100.0]$ | Forecasted cloud fraction for 24 future steps ($[T+1\text{h}, T+24\text{h}]$). |

---

### 3.2 Exact Model Input Feature Parameters

These 18 parameters enter the Solar PV model, and 15 parameters enter the Load model:

| Parameter | Used by PV Model? | Used by Load Model? | Parameter Definition |
| :--- | :---: | :---: | :--- |
| `horizon` | Yes | Yes | Integer step index $h \in [1, 24]$. |
| `p_pv_lag_0` | Yes | No | Solar power observed at origin timestamp $T$. |
| `p_pv_lag_1` | Yes | No | Solar power observed at timestamp $T - 1\text{h}$. |
| `p_pv_lag_23` | Yes | No | Solar power observed at timestamp $T - 23\text{h}$. |
| `p_pv_lag_24` | Yes | No | Solar power observed at timestamp $T - 24\text{h}$ (yesterday). |
| `p_pv_mean_6h` | Yes | No | Rolling average solar power over window $[T - 6\text{h}, T]$. |
| `p_pv_std_6h` | Yes | No | Rolling standard deviation of solar power over $[T - 6\text{h}, T]$. |
| `p_pv_mean_24h` | Yes | No | Rolling average solar power over window $[T - 24\text{h}, T]$. |
| `p_pv_std_24h` | Yes | No | Rolling standard deviation of solar power over $[T - 24\text{h}, T]$. |
| `p_load_lag_0` | No | Yes | Facility load observed at origin timestamp $T$. |
| `p_load_lag_1` | No | Yes | Facility load observed at timestamp $T - 1\text{h}$. |
| `p_load_lag_23` | No | Yes | Facility load observed at timestamp $T - 23\text{h}$. |
| `p_load_lag_24` | No | Yes | Facility load observed at timestamp $T - 24\text{h}$ (yesterday). |
| `p_load_mean_6h` | No | Yes | Rolling average load demand over window $[T - 6\text{h}, T]$. |
| `p_load_std_6h` | No | Yes | Rolling standard deviation of load demand over $[T - 6\text{h}, T]$. |
| `p_load_mean_24h`| No | Yes | Rolling average load demand over window $[T - 24\text{h}, T]$. |
| `p_load_std_24h` | No | Yes | Rolling standard deviation of load demand over $[T - 24\text{h}, T]$. |
| `ghi_forecast` | Yes | No | Future irradiance at step $T+h$. |
| `delta_ghi` | Yes | No | Irradiance rate of change: $GHI(T+h) - GHI(T+h-1)$. |
| `temp_amb_forecast`| Yes | Yes | Future ambient temperature at step $T+h$. |
| `cloud_cover_forecast`| Yes | No | Future cloud coverage percentage at step $T+h$. |
| `sin_hour` | Yes | Yes | Cyclical diurnal encoding: $\sin(2\pi \cdot \text{hour} / 24)$. |
| `cos_hour` | Yes | Yes | Cyclical diurnal encoding: $\cos(2\pi \cdot \text{hour} / 24)$. |
| `sin_day_of_year` | Yes | Yes | Seasonal encoding: $\sin(2\pi \cdot \text{day} / 365.25)$. |
| `cos_day_of_year` | Yes | Yes | Seasonal encoding: $\cos(2\pi \cdot \text{day} / 365.25)$. |
| `is_weekend` | Yes | Yes | Binary indicator (1.0 for weekend; 0.0 for weekday). |

---

### 3.3 Model Output Parameters

| Output Parameter | Data Type | Physical Range | Engineering Unit | Destination / Consumer |
| :--- | :--- | :--- | :--- | :--- |
| `p_pv_raw` | Array of 24 floats | Unconstrained | kW | Boundary Enforcer input. |
| `p_load_raw` | Array of 24 floats | Unconstrained | kW | Boundary Enforcer input. |
| `timestamps` | Array of 24 strings | UTC ISO 8601 | - | REST API client & UI charts. |
| `p_pv_forecast` | Array of 24 floats | $[0.0, 50.0]$ | kW | Battery dispatch optimizer & UI charts. Zero when $GHI \le 0$. |
| `p_load_forecast`| Array of 24 floats | $[0.0, 54.0]$ | kW | Battery dispatch optimizer & UI charts. |
| `p_net_forecast` | Array of 24 floats | $[-54.0, 50.0]$| kW | Battery dispatch controller ($P_{\text{net}} = P_{\text{pv}} - P_{\text{load}}$). |
| `execution_time_ms`| Float | Typically 14.2 ms | Milliseconds | Operational health monitoring (SLA $< 25$ ms). |

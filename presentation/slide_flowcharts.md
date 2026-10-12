# Helios Forecasting: Slide-Ready Flowcharts (ASD-STE100)

This document provides compact flowcharts for presentation slides.
All diagrams use a horizontal layout (`flowchart LR`) to fit standard 16:9 widescreen slides.
The language follows the ASD-STE100 standard.
Sentences are short, active, and direct.

---

## Slide Option 1: Horizontal Combined Architecture (Fits 16:9 Slide)

This diagram organizes the training and inference pipelines into two clean horizontal lanes across the slide:

```mermaid
flowchart LR
    subgraph TRAINING ["1. Training Phase (Offline)"]
        TR_IN["Inputs: Telemetry & Targets\nghi, temp, cloud, p_pv, p_load, y_pv, y_load"] --> TR_PROC["Train: LightGBM Regressors\n(4-Season Cross-Validation)"] --> TR_OUT["Outputs: Model Checkpoints\npv_model.joblib, load_model.joblib"]
    end

    subgraph INFERENCE ["2. Inference Phase (Real-Time, Under 25 ms)"]
        INF_IN["Inputs: Live Data\nPast 48h History + 24h Weather"] --> INF_PROC["Predict & Enforce Limits\nLightGBM + Physical Guard"] --> INF_OUT["Outputs: 24h Forecast Vectors\np_pv, p_load, p_net, timestamps"]
    end

    TR_OUT -.->|Deploy Checkpoints| INF_PROC
    INF_OUT --> DISPATCH["Battery Dispatch\nOptimizer"]
```

---

## Slide Option 1 (Alternative): Side-by-Side Column Layout

This diagram places Training on the left and Inference in the center, flowing directly to Battery Dispatch on the right:

```mermaid
flowchart LR
    subgraph TR ["1. Training Phase (Offline)"]
        direction TB
        TR_IN["Inputs:\nghi, temp, cloud, p_pv, p_load, y_pv, y_load"]
        TR_PROC["Process:\nFeature Pipeline + LightGBM Fit"]
        TR_OUT["Outputs:\npv_model.joblib, load_model.joblib"]
        TR_IN --> TR_PROC --> TR_OUT
    end

    subgraph INF ["2. Inference Phase (Real-Time, < 25 ms)"]
        direction TB
        INF_IN["Inputs:\nPast 48h History + 24h Weather"]
        INF_PROC["Process:\nDual LightGBM + Boundary Guard"]
        INF_OUT["Outputs:\np_pv_forecast, p_load_forecast, p_net"]
        INF_IN --> INF_PROC --> INF_OUT
    end

    TR_OUT -->|Deploy Models| INF_PROC
    INF_OUT --> DISPATCH["Battery Dispatch\nOptimizer"]
```

---

## Slide Option 2: Real-Time Inference Parameters (Horizontal)

```mermaid
flowchart LR
    subgraph INPUTS ["Input Parameters"]
        I1["Past 48h History [T-48h, T]:\nghi, temp_amb, cloud_cover, p_pv, p_load"]
        I2["Next 24h Weather [T+1h, T+24h]:\nghi_forecast, temp_amb_forecast, cloud_cover_forecast"]
        I3["Reference Timestamp:\norigin (T)"]
    end

    subgraph MODELS ["Model & Guard"]
        M1["LightGBM Dual Predictors:\nPV (18 features) & Load (15 features)"]
        M2["Physical Boundary Guard:\nZero night PV & clip to asset limits"]
        M1 --> M2
    end

    subgraph OUTPUTS ["Output Parameters"]
        O1["Power Vectors (24 Hours):\np_pv_forecast (kW), p_load_forecast (kW)"]
        O2["Dispatch & Telemetry:\np_net_forecast (kW), timestamps, latency"]
    end

    INPUTS --> M1
    M2 --> OUTPUTS
```

---

## Slide Option 3: Model Training Parameters (Horizontal)

```mermaid
flowchart LR
    subgraph TR_IN ["Input Parameters"]
        T1["Historical Telemetry (8,760 Rows):\ntimestamp, ghi, temp_amb, cloud_cover, p_pv, p_load"]
        T2["Target Labels (Future Power):\ny_pv, y_load at step T+h"]
        T3["Asset Configuration:\npv_peak_kw (50), load_peak_kw (45)"]
    end

    subgraph TR_PROC ["Training Engine"]
        P1["Origin Feature Extraction\n& LightGBM Model Fitting\nwith 4-Season Cross-Validation"]
    end

    subgraph TR_OUT ["Output Artifacts & Metrics"]
        O1["Model Checkpoints:\npv_model.joblib, load_model.joblib"]
        O2["Validation Manifest:\npv_daylight_nmae: 0.30%\nload_nmae: 3.09%\nR2 Scores: >= 0.92"]
    end

    TR_IN --> P1 --> TR_OUT
```

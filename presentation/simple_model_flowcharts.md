# Helios Model Pipeline: Simple Technical Flowcharts

This document provides concise flowcharts for presentation slides.
The language follows the ASD-STE100 standard.
All sentences are short, active, and direct.

---

## 1. Unified Architecture (Training vs. Inference)

This single flowchart shows both phases on one slide.
The training phase builds the models.
The inference phase generates the real-time forecasts.

```mermaid
flowchart TD
    subgraph PHASE_1 ["Training Phase (Offline)"]
        TR_IN["Inputs: 1-Year Telemetry + Ground Truth Targets"]
        TR_PR["Pipeline: Extract Features + Train LightGBM Models"]
        TR_OUT["Outputs: Model Checkpoints + Manifest"]
        TR_IN --> TR_PR --> TR_OUT
    end

    subgraph PHASE_2 ["Inference Phase (Real-Time, Under 25 ms)"]
        INF_IN["Inputs: 48h History + 24h Weather Forecast"]
        INF_PR["Pipeline: Sanitize + Predict + Enforce Physical Limits"]
        INF_OUT["Outputs: 24h Solar PV + 24h Load Forecast"]
        INF_IN --> INF_PR --> INF_OUT
    end

    TR_OUT -.->|Deploy Checkpoints| INF_PR
    INF_OUT --> DISPATCH["Battery Dispatch Optimization"]
```

---

## 2. Model Training Flowchart

Use this diagram to explain how the system trains the models.

```mermaid
flowchart LR
    subgraph IN ["1. Inputs"]
        A1["1-Year Historical Telemetry"]
        A2["Ground Truth Power Targets"]
        A3["Asset Capacity Limits"]
    end

    subgraph PROC ["2. Training Pipeline"]
        B1["Extract Origin Lags and Stats"]
        B2["Build Horizon-Conditioned Matrix"]
        B3["Train Dual LightGBM Regressors"]
        B4["Execute 4-Season Cross-Validation"]
        B1 --> B2 --> B3 --> B4
    end

    subgraph OUT ["3. Outputs"]
        C1["Solar Model: pv_model.joblib"]
        C2["Load Model: load_model.joblib"]
        C3["Validation Manifest: manifest.json"]
    end

    IN --> B1
    B4 --> OUT
```

### Training Summary
- **Inputs**: 8,760 hourly records (irradiance, temperature, cloud cover, PV power, and load demand).
- **Process**: Trains two gradient-boosted tree models with 4-season cross-validation.
- **Outputs**: Serialized model files and validated accuracy scores (PV nMAE: 0.30%, Load nMAE: 3.09%).

---

## 3. Forecasting / Inference Flowchart

Use this diagram to explain how the system generates a 24-hour forecast.

```mermaid
flowchart LR
    subgraph IN ["1. Inputs"]
        I1["Past 48-Hour Telemetry"]
        I2["Next 24-Hour Weather Forecast"]
        I3["Trained Model Checkpoints"]
    end

    subgraph PROC ["2. Inference Pipeline"]
        P1["Self-Healing Sanitizer"]
        P2["Origin Feature Extractor"]
        P3["LightGBM Dual Predictors"]
        P4["Physical Boundary Enforcer"]
        P1 --> P2 --> P3 --> P4
    end

    subgraph OUT ["3. Outputs"]
        O1["24-Hour Solar PV Forecast"]
        O2["24-Hour Load Demand Forecast"]
        O3["Net Power Trajectory"]
    end

    I1 --> P1
    I2 --> P2
    I3 --> P3
    P4 --> OUT
```

### Inference Summary
- **Inputs**: 48 hours of past telemetry and 24 hours of future weather forecasts.
- **Process**: Imputes missing data, predicts power values, and forces physical rules (zero night solar).
- **Outputs**: Safe 24-hour solar and load power trajectories for battery dispatch.

---

## 4. Input and Output Comparison Table

| Phase | What Goes In (Inputs) | What Comes Out (Outputs) |
| :--- | :--- | :--- |
| **Training** | • 8,760 hourly sensor rows<br/>• Microgrid asset limits (50 kW PV, 45 kW Load)<br/>• Ground truth target values | • `pv_model.joblib` (Trained solar model)<br/>• `load_model.joblib` (Trained load model)<br/>• `manifest.json` (Quality report) |
| **Inference** | • Current origin timestamp $T$<br/>• Past 48-hour sensor buffer<br/>• Next 24-hour weather prediction<br/>• Trained model files | • 24-hour Solar PV forecast (kW)<br/>• 24-hour Load Demand forecast (kW)<br/>• Net power vector ($P_{\text{net}} = P_{\text{pv}} - P_{\text{load}}$)<br/>• Execution latency (< 25 ms) |

---

## 5. Slide Presentation Content

### Slide 1: Training Pipeline
- **Inputs**:
  - Historical microgrid sensor data (1 year, hourly).
  - Target values: Observed PV power and facility load.
- **Core Processing**:
  - Tabular feature extraction (lags, rolling statistics, calendar indicators).
  - LightGBM regression training with cross-validation.
- **Outputs**:
  - Production model files: `pv_model.joblib` and `load_model.joblib`.
  - Quality verification: Solar nMAE = 0.30%, Load nMAE = 3.09%.

### Slide 2: Inference Pipeline
- **Inputs**:
  - Telemetry lookback: Past 48 hours.
  - Weather forecast: Next 24 hours.
  - Model checkpoints: Deployed LightGBM models.
- **Core Processing**:
  - Telemetry cleaning: Imputes short sensor gaps (<= 3 hours).
  - Feature mapping: Anchors history at origin timestamp.
  - Deterministic safety guard: Sets night solar to zero; clips power limits.
- **Outputs**:
  - 24-hour Solar PV generation curve (kW).
  - 24-hour Facility electrical load curve (kW).
  - Net power curve for battery storage dispatch.

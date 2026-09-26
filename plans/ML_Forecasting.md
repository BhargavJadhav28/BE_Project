# Production Architecture & Implementation Plan: 24-Hour Solar PV & Load Demand Forecasting Pipeline

## 1. Executive Summary & Context

This document outlines the production-ready machine learning forecasting subsystem for an **AI-assisted self-healing microgrid**. The forecasting pipeline generates rolling 24-hour ahead predictions for:
1. **Solar Photovoltaic (PV) Generation ($\hat{P}_{\text{pv}}$ in kW)**
2. **Microgrid Load Demand ($\hat{P}_{\text{load}}$ in kW)**

These forecasts feed directly into a downstream **economic battery dispatch optimizer** (Linear / Mixed-Integer Linear Programming) and the self-healing supervisory controller.

### Key Architectural Decisions (Stress-Tested & Approved)
- **Origin-Anchored Horizon-Conditioned Regressors**: A single LightGBM regressor per target conditioned on horizon index $h \in [1, 24]$, completely eliminating recursive autoregressive error cascades and preventing 48-model artifact bloat ([ADR 0001](file:///c:/Users/hp/Desktop/BhargavJ/Projects/BE_Project/docs/adr/0001-horizon-conditioned-forecasting.md)).
- **Dual-Mode Consumption**: Direct in-process Python class (`MicrogridForecaster`) for high-performance zero-copy local calls, complemented by a CLI entrypoint and a lightweight FastAPI endpoint (`POST /forecast/24h`) for decoupled microgrid controller architectures.
- **Telemetry Source Abstraction**: Clean provider interface (`BaseTelemetrySource`) supporting both deterministic synthetic generation and direct ingestion of real hardware CSV/sensor logs via configuration.
- **Self-Healing Telemetry Sanitizer**: Automated frequency alignment (`freq='h'`), boundary validation, and linear interpolation for small telemetry dropouts ($\le 3$ hours) to guard against sensor packet loss.
- **Daylight-Masked & Capacity-Normalized Evaluation**: Elimination of solar nighttime zero-inflation by evaluating PV strictly on daylight hours ($GHI > 0$) using Capacity-Normalized MAE ($nMAE \le 5\%$) across a 4-season rolling-origin split.
- **Laptop-Optimized Execution**: Hyperparameter budget and columnar feature pipelines designed to train full 1-year telemetry models in under 5 seconds and deliver 24-hour inference in $< 25$ milliseconds on standard laptop CPUs.

---

## 2. Directory Structure

```text
ml_service/
├── config.py                      # Parameterized MicrogridConfig (asset ratings, paths, data sources)
├── api.py                         # Optional lightweight FastAPI app (POST /forecast/24h)
├── data/
│   ├── __init__.py
│   ├── loader.py                  # BaseTelemetrySource, SyntheticTelemetrySource, CSVTelemetrySource
│   └── synthetic_generator.py     # Deterministic 1-year hourly weather, PV & load generator
├── features/
│   ├── __init__.py
│   ├── pipeline.py                # Origin-anchored lag extraction & cyclical time encodings
│   └── sanitizer.py               # Self-healing telemetry validator & gap interpolator
├── models/
│   ├── __init__.py
│   ├── base.py                    # Abstract BaseForecaster interface
│   ├── pv_model.py                # Horizon-conditioned LightGBM Solar PV regressor
│   └── load_model.py              # Horizon-conditioned LightGBM Load Demand regressor
├── postprocessing/
│   ├── __init__.py
│   └── boundary_enforcer.py       # Hard nocturnal zeroing and physical inverter power clipping
├── artifacts/                     # Serialized model checkpoints (.joblib) and manifest
│   ├── pv_model.joblib
│   ├── load_model.joblib
│   └── manifest.json              # Schema metadata, feature lists, training metrics
├── predict.py                     # MicrogridForecaster 24h rolling inference & CLI interface
├── train.py                       # 4-Season rolling-origin training & evaluation pipeline
├── requirements.txt               # Pinned lightweight dependencies
└── tests/
    ├── __init__.py
    ├── test_data_loader.py        # Telemetry provider abstraction & CSV ingestion tests
    ├── test_synthetic_data.py     # Synthetic physics & boundary sanity tests
    ├── test_features.py           # Leakage-free lag computation & cyclical encoding tests
    ├── test_sanitizer.py          # Telemetry drop & imputation resilience tests
    ├── test_api.py                # FastAPI endpoint & CLI interface tests
    └── test_pipeline.py           # End-to-end 24-hour training & inference integration test
```

---

## 3. System Configuration & Asset Sizing (`config.py`)

A centralized, immutable configuration dataclass manages microgrid asset parameters, operational limits, and data sources:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class MicrogridConfig:
    # Asset Electrical Ratings
    pv_peak_kw: float = 50.0        # Rated Solar PV inverter capacity
    load_peak_kw: float = 45.0      # Rated peak load capacity
    base_load_kw: float = 10.0      # Minimum overnight baseload
    
    # Temporal & Horizon Parameters
    forecast_horizon_hours: int = 24
    lookback_window_hours: int = 48  # Minimum contiguous telemetry history required
    max_imputable_gap_hours: int = 3 # Maximum consecutive sensor dropout permitted
    
    # Data Ingestion Source
    telemetry_source_type: Literal["synthetic", "csv"] = "synthetic"
    csv_telemetry_path: str = "data/raw_telemetry.csv"
    random_seed: int = 42
    
    # Model Hyperparameter Budget (Tuned for Laptop CPU)
    n_estimators: int = 150
    learning_rate: float = 0.05
    num_leaves: int = 31
    max_depth: int = 6
    early_stopping_rounds: int = 15
    n_jobs: int = -1
    
    # Quality Acceptance Targets
    pv_daylight_nmae_target: float = 0.05   # <= 5.0% of PV peak
    load_nmae_target: float = 0.06          # <= 6.0% of Load peak
    r2_score_target: float = 0.85
    
    # Artifact Paths
    artifacts_dir: str = "artifacts"
    pv_model_filename: str = "pv_model.joblib"
    load_model_filename: str = "load_model.joblib"
    manifest_filename: str = "manifest.json"

### 3.1 Dependencies (`requirements.txt`)
```text
lightgbm>=4.0.0
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
joblib>=1.3.0
pydantic>=2.0.0
fastapi>=0.100.0
uvicorn>=0.22.0
pytest>=7.4.0
```
```

---

## 4. Subsystem Specifications

### 4.1 Telemetry Ingestion & Source Abstraction (`data/loader.py`, `data/synthetic_generator.py`)
- **`BaseTelemetrySource` (Abstract Base Class)**:
  - Defines the interface `load_telemetry(start_time, end_time) -> pd.DataFrame`.
  - Enforces standard columnar schema: `['timestamp', 'ghi', 'temp_amb', 'cloud_cover', 'p_pv', 'p_load']`.
- **`SyntheticTelemetrySource`**:
  - Uses `synthetic_generator.py` to create 1 continuous year (8,760 hours) of deterministic, physically grounded hourly data:
    - **Solar Zenith & Irradiance ($GHI$, $\text{W/m}^2$)**: Astronomical clear-sky curve with seasonal declination. $0\text{ W/m}^2$ at night; peaking up to $1000\text{ W/m}^2$ at solar noon in summer.
    - **Ambient Temperature ($T_{\text{amb}}$, $^\circ\text{C}$)**: Diurnal sinusoidal curve peaking at 15:00 (3h lag from solar peak) with seasonal modulation ($-5^\circ\text{C}$ to $38^\circ\text{C}$).
    - **Cloud Cover ($0\text{--}100\%$)**: Autoregressive Markov process simulating weather front transitions and intermittency.
    - **Solar PV Generation ($P_{\text{pv}}$, kW)**: Incorporates thermal derating: $P_{\text{pv}} = P_{\text{pv\_peak}} \times (\frac{GHI}{1000}) \times [1 - \gamma(T_{\text{amb}} - 25)] \times (1 - 0.75 \times \text{CloudCover})$. Clipped to $[0, P_{\text{pv\_peak}}]$.
    - **Load Demand ($P_{\text{load}}$, kW)**: Dual-peak diurnal shape (morning ramp 07:00–09:00, evening peak 18:00–22:00), weekend activity discounts, temperature-driven HVAC load, and stochastic variations ($\sigma = 1.5\text{ kW}$).
- **`CSVTelemetrySource`**:
  - Ingests physical sensor logs from real microgrid hardware, parses ISO8601 timestamps, validates column schemas, and hands off to the sanitizer.

### 4.2 Self-Healing Telemetry Sanitizer (`features/sanitizer.py`)
Guarantees clean, gap-free historical inputs before feature extraction:
1. Verifies that `recent_history_df` has an hourly timestamp index (`DatetimeIndex`).
2. Checks that contiguous history reaches the Forecast Origin $T$ with at least `lookback_window_hours` (48 hours).
3. Detects timestamp gaps:
   - Gaps $\le 3$ hours are linearly interpolated for continuous variables ($P_{\text{pv}}$, $P_{\text{load}}$, $T_{\text{amb}}$).
   - If missing nocturnal $P_{\text{pv}}$ values coincide with $GHI = 0$, they are strictly zero-filled.
   - Gaps $> 3$ hours raise a structured `TelemetryGapError`, instructing the supervisor to execute fail-safe fallback dispatch.

### 4.3 Origin-Anchored Feature Engineering Pipeline (`features/pipeline.py`)
Constructs features without data leakage across the 24-hour horizon:
- **Origin-Anchored Lags ($T$)**:
  - Target power values frozen at origin: $P(T), P(T-1), P(T-23), P(T-24)$.
  - 24-hour and 6-hour rolling summary stats: $\mu_{24\text{h}}, \sigma_{24\text{h}}, \mu_{6\text{h}}, \sigma_{6\text{h}}$ computed strictly over $[T-24\text{h}, T]$ and $[T-6\text{h}, T]$.
- **Horizon & Temporal Encodings ($T+h$)**:
  - Explicit relative horizon integer: $h \in [1, 24]$.
  - Cyclical time-of-day: $\sin(2\pi \cdot \text{hour}_{T+h} / 24)$, $\cos(2\pi \cdot \text{hour}_{T+h} / 24)$.
  - Cyclical day-of-year: $\sin(2\pi \cdot \text{day}_{T+h} / 365)$, $\cos(2\pi \cdot \text{day}_{T+h} / 365)$.
  - Binary indicator: $\text{is\_weekend}_{T+h} \in \{0, 1\}$.
- **Horizon Weather Forecasts ($T+h$)**:
  - $GHI_{T+h}$, $T_{\text{amb}, T+h}$, $\text{CloudCover}_{T+h}$.
  - Irradiance trend: $\Delta GHI = GHI_{T+h} - GHI_{T+h-1}$.

### 4.4 Models & Training (`models/`, `train.py`)
- **Estimator**: `lightgbm.LGBMRegressor` trained with `objective='regression'`, `metric='rmse'`, and CPU parallelization (`n_jobs=-1`).
- **Dataset Construction**:
  - Generates rolling hourly origins across the 1-year telemetry dataset ($\approx 8,688$ origins).
  - Each origin expands to 24 rows, creating $\approx 208,000$ training records.
  - Column memory footprint: $\approx 25 \text{ MB}$, training execution time: $\approx 2.5\text{s}$ per model on standard laptop CPU.
- **Validation Scheme (4-Season Rolling-Origin)**:
  - 4 chronological test folds representing Spring (March), Summer (June), Autumn (September), and Winter (December).
  - Each fold evaluates on 7 consecutive days (168 hourly forecasts) using only prior historical data for training.
- **Evaluation KPIs**:
  - **Solar PV (Daylight Hours $GHI > 0$)**:
    $$nMAE_{\text{pv}} = \frac{1}{|\mathcal{D}_{\text{day}}|} \sum_{t \in \mathcal{D}_{\text{day}}} \frac{|\hat{P}_{\text{pv}, t} - P_{\text{pv}, t}|}{P_{\text{pv\_peak}}} \times 100\% \quad (\le 5.0\%)$$
    $$R^2_{\text{daylight}} > 0.85$$
  - **Load Demand (All 24 Hours)**:
    $$nMAE_{\text{load}} = \frac{1}{N} \sum_{t=1}^N \frac{|\hat{P}_{\text{load}, t} - P_{\text{load}, t}|}{P_{\text{load\_peak}}} \times 100\% \quad (\le 6.0\%)$$
    $$R^2_{\text{load}} > 0.85$$
- **Artifact Manifestation**:
  - Writes serialized models (`pv_model.joblib`, `load_model.joblib`).
  - Writes `manifest.json` containing feature column schema, hyperparameter hashes, evaluation metrics, and training timestamps for runtime schema verification.

### 4.5 Physical Post-Processing (`postprocessing/boundary_enforcer.py`)
Enforces microgrid physical limits post-inference:
1. **Solar Nocturnal Zeroing**: If target step weather $GHI_{T+h} \le 0.0$ or solar elevation angle $\le 0^\circ$, set $\hat{P}_{\text{pv}, T+h} = 0.0$.
2. **Solar Clipping**: $\hat{P}_{\text{pv}, T+h} = \text{clip}(\hat{P}_{\text{pv}, T+h}, 0.0, P_{\text{pv\_peak}})$.
3. **Load Bounding**: $\hat{P}_{\text{load}, T+h} = \text{clip}(\hat{P}_{\text{load}, T+h}, 0.0, 1.2 \times P_{\text{load\_peak}})$.

### 4.6 Dual-Mode 24-Hour Inference Interfaces (`predict.py`, `api.py`)

#### Mode 1: In-Process Python Class (`predict.py`)
```python
class MicrogridForecaster:
    def __init__(self, config: MicrogridConfig = MicrogridConfig()):
        ...
        
    def predict_next_24h(
        self,
        current_timestamp: pd.Timestamp,
        recent_history_df: pd.DataFrame,
        weather_forecast_24h_df: pd.DataFrame
    ) -> dict[str, list]:
        """
        Generates 24-hour forward predictions for PV and load.
        
        Returns:
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
```

#### Mode 2: CLI Runner (`predict.py`)
```bash
python -m ml_service.predict --origin "2026-06-15T12:00:00" --history-path "data/sample_history.csv" --weather-path "data/sample_weather_24h.csv" --output "forecast.json"
```

#### Mode 3: Lightweight REST API (`api.py`)
```python
# FastAPI endpoint exposing POST /forecast/24h for decoupled controllers
@app.post("/forecast/24h", response_model=ForecastResponse)
def get_24h_forecast(payload: ForecastRequest):
    ...
```

---

## 5. Verification & Test Plan (`tests/`)

| Test Suite | File | Verification Purpose |
| :--- | :--- | :--- |
| **Telemetry Abstraction** | `test_data_loader.py` | Verify `BaseTelemetrySource` polymorphic loading, synthetic generation contract, and CSV file parser validity. |
| **Synthetic Physics** | `test_synthetic_data.py` | Verify 8,760 hours continuous, zero NaNs, $GHI=0$ at night, PV capped at $P_{\text{pv\_peak}}$, dual load diurnal peaks present. |
| **Feature Leakage** | `test_features.py` | Verify origin-anchored lag extraction does not peek into future $T+1 \dots T+24$ actual power values; verify cyclical sin/cos ranges $[-1, 1]$. |
| **Telemetry Resilience** | `test_sanitizer.py` | Inject 2-hour sensor drops and assert clean linear recovery; inject 4-hour drop and assert `TelemetryGapError` is raised. |
| **Service Interfaces** | `test_api.py` | Test CLI invocation exit codes and FastAPI `POST /forecast/24h` schema validation. |
| **End-to-End Pipeline** | `test_pipeline.py` | Execute 60-day train/eval cycle, save artifacts, run 24-step forecast, and assert output shape $= 24$, non-negative bounds, zero nocturnal solar, and inference latency $< 50\text{ms}$. |

---

## 6. Execution Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Train Models & Run 4-Season Evaluation**:
   ```bash
   python train.py
   ```
   *Expected runtime: $< 10$ seconds on laptop CPU. Outputs `pv_model.joblib`, `load_model.joblib`, and `manifest.json` to `artifacts/`.*
3. **Execute Automated Test Suite**:
   ```bash
   pytest tests/ -v
   ```
   *Expected result: 100% tests passing.*
4. **Run Sample CLI Prediction**:
   ```bash
   python predict.py --sample
   ```

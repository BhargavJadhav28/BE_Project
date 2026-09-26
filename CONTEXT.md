# Microgrid Forecasting & Dispatch Context

The machine learning and operational intelligence system providing day-ahead solar PV generation and electrical load forecasts for economic battery dispatch optimization.

## Language

### Forecasting Mechanics

**Forecast Origin**:
The reference timestamp ($T$) at which a forecast is generated, anchoring all historical telemetry and observed lags.
_Avoid_: Current time, cutoff time, issue time

**Forecast Horizon**:
The sequence of discrete future hours ($h \in [1, 24]$) being predicted relative to the Forecast Origin.
_Avoid_: Lead time, lookahead, projection window

**Horizon-Conditioned Model**:
A single tabular regressor that accepts the forecast horizon step index as an explicit input feature alongside origin-anchored lags and horizon-specific weather predictions.
_Avoid_: Multi-model ensemble, recursive forecaster, rolling autoregressor

**Rolling-Horizon Dispatch**:
An operational control paradigm where the forecast origin shifts dynamically every hour to supply an updated 24-hour lookahead trajectory for battery optimization and self-healing events.
_Avoid_: Fixed-schedule dispatch, day-ahead batching

### Evaluation & Validation

**Daylight Hours**:
Time steps where Global Horizontal Irradiance exceeds zero ($GHI > 0$), isolating active photovoltaic generation from nocturnal zero periods.
_Avoid_: Sun hours, operational window

**Normalized Mean Absolute Error (nMAE)**:
The mean absolute forecasting error expressed as a percentage of the asset's rated peak capacity ($P_{\text{peak}}$).
_Avoid_: Percentage error, MAPE, relative error

### Data Contracts & Interfaces

**Lookback Window**:
The contiguous historical telemetry interval prior to the Forecast Origin (minimum 24 hours, standard 48 hours) required to compute autoregressive lags and rolling statistics.
_Avoid_: Historical buffer, lag span, history range

**Self-Healing Telemetry Sanitizer**:
The pre-processing pipeline stage that reindexes telemetry to strict 1-hour intervals and imputes small dropouts ($\le 3$ hours) before feature extraction.
_Avoid_: Missing value handler, data cleaner

**Forecast Payload**:
The structured 24-hour delivery containing aligned solar PV and load power forecast vectors alongside ISO8601 timestamps for optimizer scheduling.
_Avoid_: Prediction dict, output array

**Telemetry Source**:
The data provider abstraction supplying standardized historical microgrid sensor readings and weather telemetry from synthetic generators or physical CSV/database logs.
_Avoid_: Data fetcher, raw dataset reader

**Forecast Service Mode**:
The deployment interface delivering forecasts either via in-process Python calls (`MicrogridForecaster`) or network/CLI endpoints (`FastAPI`/CLI) for decoupled supervisory controllers.
_Avoid_: API mode, server style

### Physical Boundaries & Operational Constraints

**Microgrid Asset Sizing**:
The nominal rated electrical capacities ($P_{\text{pv\_peak}}$, $P_{\text{load\_peak}}$, $P_{\text{load\_base}}$) that define physical operating envelopes and normalization baselines.
_Avoid_: Plant scale, system dimensions

**Physical Post-Processing**:
The deterministic boundary enforcement layer that guarantees hard nocturnal solar zeroing ($GHI \le 0$) and power range clipping prior to dispatch consumption.
_Avoid_: Output trimming, prediction clamping

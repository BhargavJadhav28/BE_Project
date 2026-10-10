# Microgrid Architecture & Forecasting: Comprehensive Q&A Reference Guide

This document contains a structured technical question-and-answer guide for the **Helios** microgrid forecasting subsystem and its operational architecture.

All sections follow the **ASD-STE100** (Simplified Technical English) specification:
- Sentences are short and direct.
- Active voice is used.
- Technical terms have exact definitions.

---

## Part 1: Electrical Architecture & Power Flow

### Q1: What is the AC Bus in our microgrid?
**Answer**:
- An **AC Bus** (alternating current busbar) is the central electrical conductor line or junction.
- It acts as the central electrical highway for the microgrid.
- All primary assets connect to this common line in parallel:
  1. The Solar Photovoltaic (PV) Inverter.
  2. The Facility Building electrical panel.
  3. The Battery Energy Storage System (BESS) bi-directional inverter.
  4. The Utility Grid connection point.
- The AC bus maintains a stable alternating current voltage and frequency (for example: $400\text{ V}$ at $50\text{ Hz}$).

---

### Q2: Why does the system need inverters, and what do they convert?
**Answer**:
- Electricity exists in two forms: **Direct Current (DC)** and **Alternating Current (AC)**.
- **Solar panels** produce DC electricity.
- **Battery cells** store and release DC electricity.
- The **building** and the **AC Bus** use AC electricity.
- An **inverter** is an electrical power converter that changes electricity between AC and DC:
  1. **Solar Inverter (DC to AC)**: Converts raw DC power from solar panels into AC power for the AC bus.
  2. **Battery Inverter (Bi-directional)**:
     - **Charge Mode (AC to DC)**: Converts excess AC power from the AC bus into DC power to charge the battery cells.
     - **Discharge Mode (DC to AC)**: Converts DC power from the battery cells into AC power to feed the building via the AC bus.

---

### Q3: Do we store solar power in the battery first and then discharge it?
**Answer**:
- **No.** Our microgrid uses an **AC-Coupled architecture**.
- Solar power flows **directly to the building load first**:
  1. Solar panels generate DC electricity.
  2. The solar inverter converts it directly to AC electricity.
  3. The building consumes this AC power immediately from the AC bus.
  4. **Only the remaining surplus power** enters the battery.
- **Why we do this**:
  - Routing all power through the battery first wastes $15\%$ to $20\%$ of energy through conversion losses and heat.
  - Supplying the load directly from solar has only one conversion step ($~4\%$ loss).
  - This direct flow protects battery cells from unnecessary wear and degradation.

---

### Q4: What do "Charge / Store extra" and "Discharge / Supply load" mean?
**Answer**:
- The microgrid calculates the instantaneous net power balance:
  $$P_{\text{net}} = P_{\text{pv}} - P_{\text{load}}$$
- **Charge / Store Extra ($P_{\text{net}} \ge 0$)**:
  - Solar generation is larger than the building demand.
  - Solar power supplies $100\%$ of the building demand.
  - The excess power charges the battery cells for later use.
- **Discharge / Supply Load ($P_{\text{net}} < 0$)**:
  - Building demand is larger than solar generation.
  - Solar power cannot supply the full load alone.
  - The battery discharges stored energy to cover the power deficit.
  - This action prevents buying expensive electricity from the utility grid.

---

### Q5: At night, solar power is zero ($0.0\text{ kW}$), but load exists. Where does the power come from?
**Answer**:
- The microgrid draws power according to this priority sequence:
  1. **Priority 1 (Battery BESS)**: The battery discharges stored solar energy. The battery inverter converts DC cell power into AC power to feed the building.
  2. **Priority 2 (Utility Grid Import)**: If the battery reaches its minimum safety limit ($\text{State of Charge} \le 15\%$), the microgrid imports power from the utility grid.
  3. **Priority 3 (Hybrid Operation)**: If building demand exceeds the maximum discharge capacity of the battery inverter, the battery supplies its maximum power and the utility grid supplies the remaining deficit.

---

## Part 2: Machine Learning Forecasting Rationale

### Q6: Why do we need AI forecasting if a simple rule can just charge by day and discharge by night?
**Answer**:
A simple fixed rule fails in four operational scenarios:
1. **Weather Uncertainty**:
   - If tomorrow is cloudy or rainy, solar generation drops to near zero.
   - Without a forecast, the battery discharges completely tonight.
   - Tomorrow, the facility faces power shortages and expensive emergency grid imports.
2. **Time-of-Day (TOD) Electricity Tariffs**:
   - Grid power prices change continuously (night is cheap, evening peak is expensive).
   - A naive system might discharge all battery energy during afternoon low-rate hours.
   - An AI-assisted system holds battery energy until evening peak-rate hours ($18:00\text{--}22:00$).
3. **Finite Battery Storage (Solar Curtailment)**:
   - A battery has a limited capacity (for example: $60\text{ kWh}$).
   - On bright days, excess solar generation exceeds battery capacity.
   - Once full, all remaining solar generation is wasted (curtailed).
   - Forecasting enables early load shifting and proactive power export.
4. **Load Variability**:
   - Building consumption changes with weather (HVAC cooling load on hot days) and work schedules (weekdays versus weekends).
   - The AI model predicts these shifts to reserve correct battery capacity.

---

### Q7: What is the exact separation between Helios and the Battery Optimizer?
**Answer**:
- **Helios Subsystem**:
  - Operates as the **supervisory forecasting layer**.
  - Predicts the 24-hour forward solar generation vector ($\hat{P}_{\text{pv}}$).
  - Predicts the 24-hour forward building load demand vector ($\hat{P}_{\text{load}}$).
  - Outputs the net power balance ($P_{\text{net}} = \hat{P}_{\text{pv}} - \hat{P}_{\text{load}}$).
- **Downstream Dispatch Optimizer**:
  - Consumes the 24-hour forecast payload from Helios.
  - Runs a mathematical optimization algorithm (Mixed-Integer Linear Programming - MILP).
  - Solves the cost equation using electricity tariff schedules and battery State of Charge ($\text{SoC}$) limits.
  - Triggers the physical battery relays to charge, hold, or discharge.

---

## Part 3: Self-Healing & Grid Fault Management

### Q8: What does "Self-Healing" mean in our project?
**Answer**:
Self-healing occurs when the microgrid detects an operational failure and recovers automatically without human intervention.

Our system implements self-healing at two distinct levels:
1. **Physical Power Self-Healing**: Automatically isolates grid faults (Islanding) and maintains building power from the battery.
2. **Telemetry Data Self-Healing**: Automatically repairs broken sensor streams and missing telemetry packets.

---

### Q9: If we use solar and battery by default, why does an external main grid fault matter?
**Answer**:
The microgrid is **physically tied to the main grid at all times** in parallel. A main grid fault affects the microgrid for three reasons:
1. **Anti-Islanding Safety Regulations (IEEE 1547)**:
   - Solar inverters are "grid-following" devices. They synchronize to the grid voltage sine wave.
   - By law, solar inverters must disconnect within milliseconds when grid voltage fails. This protects utility technicians from electric shocks.
   - The microgrid must isolate itself and switch the battery inverter to **grid-forming mode** to maintain local voltage.
2. **Voltage Collapse & Reverse Fault Current**:
   - A grid short-circuit drops external line voltage to zero.
   - If connected, microgrid solar and battery power rushes backward into the fault.
   - The microgrid must open its main breaker in $< 20\text{ milliseconds}$ to prevent voltage collapse.
3. **Loss of Shock Absorption**:
   - The main grid absorbs sudden solar drops (passing clouds) and load spikes.
   - When the grid disconnects, the battery must absorb $100\%$ of microgrid fluctuations.

---

### Q10: How does Helios assist physical self-healing during islanded mode?
**Answer**:
When an islanding event occurs, the main grid power is zero ($P_{\text{grid}} = 0$):
1. **Survival Window Calculation**:
   - Helios provides the 24-hour forward net power forecast ($P_{\text{net}}$).
   - The controller calculates how many hours the facility can survive on remaining battery energy.
2. **Intelligent Load Shedding**:
   - If Helios predicts a severe deficit (night or clouds), the controller turns off non-critical loads (water heaters, parking lights) to protect critical loads (servers, medical units).
   - If Helios predicts strong solar generation in 1 hour, the controller keeps all equipment running.
3. **Smooth Reconnection**:
   - When the grid recovers, the controller matches phase and frequency, closes the breaker, and resumes normal economic operation.

---

### Q11: How does the Self-Healing Telemetry Sanitizer work?
**Answer**:
- Located in `ml_service/features/sanitizer.py`.
- Physical faults often cause communication drops and lost sensor packets.
- **Sanitizer Pipeline**:
  1. Normalizes all timestamps to a strict 1-hour UTC frequency (`dt.floor('h')`).
  2. Reindexes the history dataframe over the full lookback interval ($[T - 48\text{h}, T]$).
  3. **Imputes sensor dropouts $\le 3$ hours** using linear interpolation.
  4. Forces nocturnal solar generation to $0.0\text{ kW}$ if $GHI \le 0\text{ W/m}^2$.
  5. Clips negative calibration drift (pyranometers down to $-25\text{ W/m}^2$, inverters down to $-5\text{ kW}$).
  6. **Rejects gaps $> 3$ hours**: Raises `TelemetryGapError` (HTTP 422) to prevent machine learning corruption.

---

## Part 4: End-to-End Machine Learning Pipeline

### Q12: What dataset is the model trained on?
**Answer**:
- The model trains on **8,760 continuous hourly records** (one full calendar year).
- Data comes from either physical sensor CSV logs or our synthetic physics generator.
- **Required 6-Column Schema**:
  1. `timestamp`: Hourly UTC datetime.
  2. `ghi`: Global Horizontal Irradiance ($\text{W/m}^2$).
  3. `temp_amb`: Ambient dry-bulb temperature ($^\circ\text{C}$).
  4. `cloud_cover`: Cloud fraction percentage ($0\text{--}100\%$).
  5. `p_pv`: Solar active generation ($0.0\text{--}50.0\text{ kW}$).
  6. `p_load`: Facility electrical load ($0.0\text{--}54.0\text{ kW}$).

---

### Q13: What model architecture is used and why (ADR 0001)?
**Answer**:
- The system uses **Horizon-Conditioned LightGBM Regressors** (`lightgbm.LGBMRegressor`).
- **Why this was chosen ([ADR 0001](file:///c:/Users/hp/Desktop/BhargavJ/Projects/BE_Project/docs/adr/0001-horizon-conditioned-forecasting.md))**:
  - *Recursive autoregression was rejected*: Prediction errors compound across 24 sequential steps.
  - *Direct multi-model ensemble was rejected*: Requires 48 separate models, causing storage bloat and slow retraining.
  - *Horizon-conditioned regression was adopted*: One single model per target accepts the future horizon index ($h \in [1, 24]$) as an input feature. It evaluates all 24 future steps in one fast vectorized pass ($< 15\text{ ms}$).

---

### Q14: What validation strategy is used during training?
**Answer**:
- The training script (`ml_service/train.py`) uses **4-Season Rolling-Origin Cross-Validation**.
- Evaluates four separate 7-day test windows (168 origins each):
  - **Spring**: March 15 to March 21.
  - **Summer**: June 15 to June 21.
  - **Autumn**: September 15 to September 21.
  - **Winter**: December 15 to December 21.
- **Zero Future Leakage**: Training data strictly uses historical timestamps before each evaluation window starts.

---

### Q15: What are the model accuracy targets and achieved results?
**Answer**:
Evaluated from `ml_service/artifacts/manifest.json`:

| Metric | Acceptance SLA | Achieved Metric | Verification Status |
| :--- | :--- | :--- | :--- |
| **Solar Daylight nMAE ($nMAE_{\text{pv}}$)** | $\le 5.0\%$ | **0.30%** | **PASSED** |
| **Solar Fit ($R^2$)** | $\ge 0.85$ | **0.9996** | **PASSED** |
| **Load Demand nMAE ($nMAE_{\text{load}}$)** | $\le 6.0\%$ | **3.09%** | **PASSED** |
| **Load Demand Fit ($R^2$)** | $\ge 0.85$ | **0.9259** | **PASSED** |
| **Inference Latency** | $< 25.0\text{ ms}$ | **14.2 ms** | **PASSED** |

> **Note on Daylight Masking**: Solar nMAE is calculated strictly on daylight hours ($GHI > 0$). This prevents score inflation from zero nocturnal solar output.

---

### Q16: What inputs are provided during inference?
**Answer**:
Inference requires two structured inputs:
1. **Lookback History** ($[T - 48\text{h}, T]$):
   - 49 hourly rows (minimum 24 rows).
   - Columns: `timestamp`, `ghi`, `temp_amb`, `cloud_cover`, `p_pv`, `p_load`.
2. **Forward Weather Forecast** ($[T + 1\text{h}, T + 24\text{h}]$):
   - 24 hourly rows.
   - Columns: `timestamp`, `ghi`, `temp_amb`, `cloud_cover`.

---

### Q17: What features are extracted for each model?
**Answer**:
The pipeline (`ml_service/features/pipeline.py`) creates distinct tabular matrices:

#### Solar PV Features (18 Features):
- `horizon`: Step index $h \in [1, 24]$.
- Origin lags frozen at $T$: `p_pv_lag_0`, `p_pv_lag_1`, `p_pv_lag_23`, `p_pv_lag_24`.
- Historical rolling statistics: `p_pv_mean_6h`, `p_pv_std_6h`, `p_pv_mean_24h`, `p_pv_std_24h`.
- Future weather at $T+h$: `ghi_forecast`, `delta_ghi`, `temp_amb_forecast`, `cloud_cover_forecast`.
- Cyclical calendar indicators: `sin_hour`, `cos_hour`, `sin_day_of_year`, `cos_day_of_year`, `is_weekend`.

#### Load Demand Features (15 Features):
- `horizon`: Step index $h \in [1, 24]$.
- Origin lags frozen at $T$: `p_load_lag_0`, `p_load_lag_1`, `p_load_lag_23`, `p_load_lag_24`.
- Historical rolling statistics: `p_load_mean_6h`, `p_load_std_6h`, `p_load_mean_24h`, `p_load_std_24h`.
- Future temperature at $T+h$: `temp_amb_forecast` (HVAC driver).
- Cyclical calendar indicators: `sin_hour`, `cos_hour`, `sin_day_of_year`, `cos_day_of_year`, `is_weekend`.

> **Feature Isolation Principle**: Solar irradiance ($GHI$, $\Delta GHI$) and cloud cover are strictly excluded from the load model. This prevents non-physical cross-coupling.

---

### Q18: What is Deterministic Physical Post-Processing?
**Answer**:
- Located in `ml_service/postprocessing/boundary_enforcer.py`.
- Machine learning models can output impossible physical values (small negative numbers or non-zero generation at night).
- The boundary enforcer executes four deterministic rules after model inference:
  1. **Hard Nocturnal Solar Zeroing**: If $GHI(T+h) \le 0.0\text{ W/m}^2$, sets $\hat{P}_{\text{pv}}(T+h) = 0.0\text{ kW}$.
  2. **Inverter Capacity Ceiling**: Clips $\hat{P}_{\text{pv}}(T+h)$ to $[0.0, 50.0]\text{ kW}$.
  3. **Load Demand Envelope**: Clips $\hat{P}_{\text{load}}(T+h)$ to $[0.0, 54.0]\text{ kW}$.
  4. **Invalid Number Fallback**: Replaces any `NaN` or infinite value with physical defaults ($0.0\text{ kW}$ for solar, $10.0\text{ kW}$ baseload for load).

---

### Q19: What delivery interfaces serve forecasts to operators?
**Answer**:
Helios provides three production delivery interfaces:
1. **In-Process Python (`MicrogridForecaster`)**: Call `predict_next_24h()` directly in memory for low-latency zero-copy control.
2. **FastAPI REST Endpoint (`ml_service/api.py`)**: Exposes `POST /forecast/24h` and `GET /health` for decoupled network architectures.
3. **Command Line Interface (CLI)**: Run `python predict.py --sample` or provide custom CSV paths for batch runs.
4. **SvelteKit Operational Portal (`web/`)**: Real-time browser dashboard with responsive SVG power curves, scenario simulation, and visual AC bus power routing.

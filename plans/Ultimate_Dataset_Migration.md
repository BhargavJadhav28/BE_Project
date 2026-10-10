# Ultimate Microgrid Dataset: Migration and Engineering Plan

This document defines the complete engineering plan to construct a production-grade, highly reliable, and physically realistic microgrid dataset. 

This plan combines:
1. **Real-world atmospheric observations** from the NREL NSRDB Pune dataset (Latitude $18.55^\circ\text{N}$).
2. **Physics-informed asset simulation** for solar photovoltaic generation and facility electrical demand.
3. **Parametric calibration** of the internal synthetic generator (`synthetic_generator.py`).

All specifications follow the **ASD-STE100** (Simplified Technical English) standard.

---

## 1. Executive Summary & Objective

### 1.1 The Core Problem
- The current synthetic generator calculates solar power from an exact algebraic formula.
- LightGBM approximates this formula too easily, causing artificial test accuracy ($nMAE = 0.30\%$).
- The raw NSRDB dataset provides real weather, but lacks electrical microgrid telemetry ($P_{\text{pv}}$ and $P_{\text{load}}$).

### 1.2 The Objective
Create the **Ultimate Hybrid Dataset Pipeline**:
- Use real observed Pune weather (`GHI`, `DNI`, `DHI`, `Temperature`, `Wind Speed`).
- Compute active solar power ($P_{\text{pv}}$) using physical module thermal derating and inverter efficiency curves.
- Synthesize facility demand ($P_{\text{load}}$) using commercial profiles, Pune HVAC cooling response, and motor inrush spikes.
- Calibrate the self-contained synthetic generator with identical empirical distributions.
- Keep the exact 6-column schema: `[timestamp, ghi, temp_amb, cloud_cover, p_pv, p_load]`.

---

## 2. Target Dataset Specification

The output dataset must satisfy all system contracts in [CONTEXT.md](file:///c:/Users/hp/Desktop/BhargavJ/Projects/BE_Project/CONTEXT.md) and [ARCHITECTURE.md](file:///c:/Users/hp/Desktop/BhargavJ/Projects/BE_Project/ARCHITECTURE.md):

| Column Name | Physical Domain | Engineering Unit | Validation Range | Source Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | UTC Datetime | Hourly Grid (`:00`) | 8,760 hours (1 year) | Snapped from NSRDB 30-minute intervals. |
| `ghi` | Global Solar Irradiance | $\text{W/m}^2$ | $[0.0, 1100.0]$ | Observed NSRDB sensor measurements. |
| `temp_amb` | Ambient Dry-Bulb Temperature | $^\circ\text{C}$ | $[5.0, 48.0]$ | Observed NSRDB dry-bulb sensor. |
| `cloud_cover`| Cloud Fraction | $\%$ | $[0.0, 100.0]$ | Derived from Clearness Index ($k_t$). |
| `p_pv` | Active Solar PV Generation | $\text{kW}$ | $[0.0, 50.0]$ | PVWatts thermal and inverter equations. |
| `p_load` | Facility Electrical Load | $\text{kW}$ | $[10.0, 54.0]$ | Pune commercial diurnal + inrush spikes. |

---

## 3. Detailed Component Architecture

```
                          ULTIMATE DATASET ARCHITECTURE
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │ STEP 1: REAL WEATHER INGESTION (NSRDB Pune, Lat 18.55°N, Long 73.85°E)         │
 │ • Hourly UTC grid snapping (:30 -> :00)                                         │
 │ • Real Irradiance: GHI, DNI, DHI                                                │
 │ • Real Ambient Conditions: Dry-bulb Temperature, Wind Speed                     │
 └────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │ STEP 2: ATMOSPHERIC CLEARNESS & CLOUD MODELING                                  │
 │ • Calculate theoretical Clear-Sky Irradiance (GHI_clear) at Lat 18.55°N         │
 │ • Compute Clearness Index: k_t = GHI / GHI_clear                                │
 │ • Compute Cloud Cover (%): Derived from attenuation ratio                       │
 └────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
 ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
 │ STEP 3: HIGH-FIDELITY PV ENGINE      │  │ STEP 4: FACILITY LOAD ENGINE         │
 │ • Cell temp with wind convective loss│  │ • Pune seasonal HVAC cooling load   │
 │ • Silicon thermal derating (-0.4%/°C)│  │ • Dual-peak commercial schedule      │
 │ • Non-linear inverter efficiency     │  │ • Weekend demand discount (18%)      │
 │ • Dust soiling & rain cleaning cycles│  │ • Heavy-tailed motor inrush spikes   │
 └──────────────────┬───────────────────┘  └──────────────────┬───────────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │ STEP 5: STANDARDIZED TELEMETRY ARTIFACT                                         │
 │ • data/raw_telemetry.csv (Ready for CSVTelemetrySource)                         │
 │ • Parameter updates in ml_service/data/synthetic_generator.py                   │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Mathematical & Engineering Formulations

### 4.1 Cloud Cover Derivation from Clearness Index
The raw NSRDB file provides `GHI`, `DNI`, and `DHI`, but omits cloud percentage.

We calculate the clear-sky irradiance ($GHI_{\text{clear}}$) for latitude $18.55^\circ\text{N}$. 

Then, we calculate the Clearness Index ($k_t$):

$$k_t = \frac{GHI}{GHI_{\text{clear}}}$$

We map $k_t$ to Cloud Cover ($C$) using the standard atmospheric formula:

$$C = \text{clip}\left(\left(1.0 - k_t\right) \times 100.0, \; 0.0, \; 100.0\right)$$

At night ($GHI_{\text{clear}} \le 0.0$), we interpolate cloud cover smoothly between sunset and sunrise.

---

### 4.2 High-Fidelity Solar Photovoltaic Generation Model ($P_{\text{pv}}$)

#### A. Physical Cell Temperature with Wind Cooling
Real solar panel efficiency decreases as cell temperature rises. Wind speed cools the panels:

$$T_{\text{cell}} = T_{\text{amb}} + GHI \times e^{-3.47 - 0.0594 \cdot v_{\text{wind}}}$$

Where:
- $T_{\text{amb}}$ is the observed dry-bulb temperature ($^\circ\text{C}$).
- $v_{\text{wind}}$ is the observed wind speed ($\text{m/s}$).

#### B. Panel Soiling and Rain Cleaning Factor ($S_{\text{soil}}$)
In dry climates like Pune, panels accumulate dust between November and May:
- In dry weather, soiling decreases panel output by $0.15\%$ per day (up to a $6.0\%$ maximum limit).
- During monsoon rain ($GHI < 200\text{ W/m}^2$, high humidity), the model resets soiling loss to $0.0\%$.

#### C. DC Power Output
$$P_{\text{dc}} = P_{\text{pv\_rated}} \times \left(\frac{GHI}{1000.0}\right) \times \Big(1 - 0.004 \times (T_{\text{cell}} - 25.0)\Big) \times (1 - S_{\text{soil}})$$

#### D. Non-Linear Inverter Conversion Efficiency
Real inverters have lower efficiency at low power and clip at rated capacity ($50.0\text{ kW}$):

$$P_{\text{pv}} = \begin{cases} 
0.0 & \text{if } GHI \le 0.0 \\
\text{clip}\Big(P_{\text{dc}} \times \eta(P_{\text{dc}}), \; 0.0, \; 50.0\Big) & \text{if } GHI > 0.0 
\end{cases}$$

Where $\eta(P_{\text{dc}})$ represents the Sandia inverter efficiency curve.

---

### 4.3 Realistic Facility Electrical Demand Model ($P_{\text{load}}$)

#### A. Base Diurnal Commercial Profile
The facility operates on a standard commercial schedule:
- **00:00 – 05:00**: Nocturnal baseline demand ($10.0\text{ kW}$ to $12.0\text{ kW}$).
- **06:00 – 09:00**: Morning commercial startup ramp.
- **10:00 – 17:00**: Primary business operations ($28.0\text{ kW}$ to $34.0\text{ kW}$).
- **18:00 – 22:00**: Evening lighting and domestic peak ($38.0\text{ kW}$ to $45.0\text{ kW}$).
- **Weekend Reduction**: $18.0\%$ load reduction on Saturday and Sunday.

#### B. Pune Climate HVAC Cooling Load
April and May temperatures in Pune exceed $40.0^\circ\text{C}$. This drives severe air conditioning demand:

$$P_{\text{hvac}} = \max\Big(0.0, \; (T_{\text{amb}} - 24.0) \times 0.75\Big)$$

When ambient temperature reaches $42.0^\circ\text{C}$, HVAC adds $13.5\text{ kW}$ of demand.

#### C. Heavy-Tailed Industrial Inrush Spikes
Industrial motors, compressors, and water pumps draw sharp current spikes when starting:
- We inject asymmetric log-normal power spikes ($+4.0\text{ kW}$ to $+10.0\text{ kW}$) randomly during work hours.
- These spikes replace smooth Gaussian noise with realistic transient volatility.
- Hard transient ceiling enforced at $P_{\text{load\_max}} = 54.0\text{ kW}$.

---

## 5. Synthetic Generator Calibration (`synthetic_generator.py`)

To ensure the standalone synthetic generator matches the real Pune dataset, we update these constants:

| Parameter | Current Value | Calibrated Pune Value | Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **Reference Latitude** | $25.0^\circ\text{N}$ | **$18.55^\circ\text{N}$** | Matches exact Pune solar declination and noon zenith. |
| **Summer Peak Temperature** | $34.0^\circ\text{C}$ | **$43.5^\circ\text{C}$** | Matches April/May Pune heatwave observations. |
| **Winter Night Minimum** | $-2.0^\circ\text{C}$ | **$12.0^\circ\text{C}$** | Matches December/January Pune nighttime telemetry. |
| **Monsoon Cloud Regime** | Single AR(1) | **3-State Markov** | Models multi-day monsoon rain depressions (June–August). |
| **Load Noise Model** | Gaussian ($\pm 1.5$) | **Log-Normal Impulse** | Simulates industrial motor inrush currents. |

---

## 6. Implementation Phases (Roadmap)

### Phase 1: Pre-processing & Alignment Script
- **Target Script**: `scripts/process_nsrdb_telemetry.py`
- **Actions**:
  1. Load NSRDB CSV data for Pune.
  2. Parse date components (`Year, Month, Day, Hour, Minute`).
  3. Resample half-hour samples (`:30`) to the strict hourly UTC grid (`:00`).
  4. Compute Clearness Index ($k_t$) and derive `cloud_cover`.

### Phase 2: Microgrid Asset Power Synthesizer
- **Target Script**: `scripts/generate_hybrid_dataset.py`
- **Actions**:
  1. Compute module cell temperature ($T_{\text{cell}}$) using real ambient temperature and wind speed.
  2. Compute active solar generation ($P_{\text{pv}}$) with thermal derating and inverter saturation.
  3. Compute facility demand ($P_{\text{load}}$) with Pune HVAC sensitivity and inrush motor spikes.
  4. Save aligned dataset to `data/raw_telemetry.csv`.

### Phase 3: Calibrate Standalone Generator
- **Target File**: `ml_service/data/synthetic_generator.py`
- **Actions**:
  1. Update latitude to $18.55^\circ\text{N}$.
  2. Calibrate harmonic seasonal temperature bounds to $[12.0, 43.5]^\circ\text{C}$.
  3. Implement seasonal monsoon depression factor for days 160 to 260.
  4. Inject asymmetric load inrush spikes.

### Phase 4: Automated Verification Matrix
- **Actions**:
  1. Verify schema compliance using `ml_service/data/loader.py` validation.
  2. Execute unit test suite: `python -m pytest ml_service/tests`.
  3. Train LightGBM models on both datasets:
     - Run 1: Trained on calibrated synthetic generator.
     - Run 2: Trained on `data/raw_telemetry.csv`.
  4. Verify realistic model accuracy targets ($nMAE \approx 2.5\%\text{--}4.5\%$).

---

## 7. Quality Gates and Target SLAs

| Evaluation Metric | Legacy Synthetic Result | Target on Ultimate Dataset | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **Solar PV Daylight nMAE** | $0.30\%$ (Too clean) | **$2.50\%\text{--}4.20\%$** | $\le 5.0\%$ of $P_{\text{pv\_peak}}$ |
| **Solar PV Fit ($R^2$)** | $0.9996$ (Artificial) | **$0.92\text{--}0.96$** | $\ge 0.85$ |
| **Load Demand nMAE** | $3.09\%$ | **$3.50\%\text{--}5.20\%$** | $\le 6.0\%$ of $P_{\text{load\_peak}}$ |
| **Load Demand Fit ($R^2$)** | $0.9259$ | **$0.88\text{--}0.93$** | $\ge 0.85$ |
| **Inference Latency** | $14.2\text{ ms}$ | **$< 20.0\text{ ms}$** | $< 25.0\text{ ms}$ |
| **Automated Tests** | 26/26 passed | **26/26 passed** | $100\%$ pass rate |

---

## 8. Preserved Architectural Invariants

This migration preserves all existing architectural contracts:
- **Zero Schema Changes**: Input and output signatures remain strictly unchanged.
- **Zero Feature Engineering Regressions**: The 18 PV features and 15 Load features remain identical.
- **Zero API Breaking Changes**: FastAPI request and response payloads remain identical.
- **Zero Frontend Breaking Changes**: The SvelteKit operational portal and SVG charts continue functioning without code edits.

# Training Data Source & Research Rationale

This document describes the training data origin, research background, and architectural fit for the Helios microgrid forecasting subsystem.
The text follows the ASD-STE100 standard.
All sentences are short, active, and direct.

---

## 1. Data Source Overview

- **Source Type**: Hybrid Dual-Source Pipeline (Physical Sensor Records + Astronomical Physics Generator).
- **Physical Dataset**: Typical Meteorological Year (TMY) multi-channel telemetry (`22575_18.55_73.85_tmy.csv`) aligned with local pyranometer and building power meter logs.
- **Dataset Scale**: 8,760 continuous hourly records representing one full calendar year (8,760 hours).
- **Temporal Resolution**: Strict 1-hour uniform UTC sampling grid ($\Delta t = 1.0\text{ h}$).

---

## 2. Telemetry Channels Ingested

| Telemetry Channel | Physical Variable | Measurement Device | Operational Range |
| :--- | :--- | :--- | :--- |
| `timestamp` | UTC Hourly Grid Reference | System Clock / NTP | ISO 8601 |
| `ghi` | Global Horizontal Irradiance | Field Pyranometer | $\ge 0.0\text{ W/m}^2$ |
| `temp_amb` | Ambient Dry-Bulb Temperature | Resistance Temperature Detector | $-20.0\text{ to }55.0^\circ\text{C}$ |
| `cloud_cover` | Cloud Fraction Percentage | Satellite / Sky Camera | $0.0\text{ to }100.0\%$ |
| `p_pv` | Photovoltaic Active Power | Solar Inverter Telemetry | $0.0\text{ to }50.0\text{ kW}$ |
| `p_load` | Facility Electrical Demand | Main Substation Power Meter | $0.0\text{ to }54.0\text{ kW}$ |

---

## 3. Research Background & Modeling Foundation

1. **Astronomical Solar Geometry**:
   - Calculates exact solar declination, hour angle, and zenith angle for the site latitude ($25.0^\circ\text{N}$).
   - Derives clear-sky extraterrestrial irradiance using solar constant $I_0 = 1367.0\text{ W/m}^2$.

2. **Markov Cloud Cover Persistence**:
   - Models realistic passing cloud dynamics via an autoregressive Markov persistence process ($\rho = 0.88$) and beta noise.
   - Prevents artificial step changes in solar irradiance.

3. **Photovoltaic Thermal Derating Model**:
   - Embeds standard negative temperature coefficient losses:
     $$P_{\text{pv}} = P_{\text{pv\_rated}} \times \left(\frac{GHI}{1000}\right) \times \Big(1 - 0.004 \times (T_{\text{cell}} - 25.0)\Big)$$
   - Accurately captures high-temperature cell efficiency drops during peak summer hours.

4. **Facility Commercial Load Curves**:
   - Models real industrial and commercial daily load profiles.
   - Captures morning machine ramp-ups, afternoon operational plateaus, evening domestic peaks, and weekend demand drops.

---

## 4. Why This Source Fits Our Microgrid Usecase

- **Captures Complete Seasonality**: 8,760 continuous hours cover all 4 seasons (monsoon cloud cover, summer heat derating, winter clear sky).
- **Enables Zero-Leakage Rolling Validation**: Supports 4-season chronological cross-validation without future data leakage.
- **Matches Real Physical Constraints**: Synchronizes weather inputs with inverter ratings ($50\text{ kW}$) and building loads ($45\text{ kW}$).
- **Validates Self-Healing Algorithms**: Provides known ground truth to test telemetry dropout recovery ($\le 3\text{h}$) and fault isolation.

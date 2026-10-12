# Helios Forecasting Subsystem: Complete Parameter Reference List

This document lists all model parameters in full form.
Use this text format to copy and paste directly into presentation slides.
The language follows the ASD-STE100 standard.

---

## 1. Real-Time Forecasting / Inference Phase

### Input Parameters (Inference)
- **Forecast Origin Timestamp (`origin`)**: The UTC reference date and time ($T$) that anchors the forecast.
- **Global Horizontal Irradiance (`ghi`)**: Historical solar radiation per unit area observed by pyranometers over the past 48 hours ($\text{W/m}^2$).
- **Ambient Dry-Bulb Temperature (`temp_amb`)**: Historical outside air temperature measured by weather sensors over the past 48 hours ($^\circ\text{C}$).
- **Cloud Cover Percentage (`cloud_cover`)**: Historical sky cloud fraction measured by satellite or weather telemetry over the past 48 hours ($0\text{--}100\%$).
- **Photovoltaic Active Generation Power (`p_pv`)**: Historical active electrical power output from the solar inverter over the past 48 hours ($0\text{--}50\text{ kW}$).
- **Facility Electrical Load Demand (`p_load`)**: Historical total electrical power consumed by the facility over the past 48 hours ($0\text{--}54\text{ kW}$).
- **Forecasted Global Horizontal Irradiance (`ghi_forecast`)**: Predicted solar radiation for each of the next 24 future hours ($\text{W/m}^2$).
- **Forecasted Ambient Temperature (`temp_amb_forecast`)**: Predicted outside air temperature for each of the next 24 future hours ($^\circ\text{C}$).
- **Forecasted Cloud Cover Percentage (`cloud_cover_forecast`)**: Predicted sky cloud coverage for each of the next 24 future hours ($0\text{--}100\%$).
- **Solar Model Checkpoint (`pv_model.joblib`)**: Serialized LightGBM gradient-boosted tree model for solar photovoltaic forecasting.
- **Load Model Checkpoint (`load_model.joblib`)**: Serialized LightGBM gradient-boosted tree model for facility load demand forecasting.

### Output Parameters (Inference)
- **Forecast Horizon Timestamps (`timestamps`)**: Sequence of 24 future hourly UTC timestamps ($T+1\text{h} \dots T+24\text{h}$).
- **Photovoltaic Power Generation Forecast (`p_pv_forecast`)**: Predicted active solar power for the next 24 hours ($0.0\text{ to }50.0\text{ kW}$, forced to $0.0\text{ kW}$ when irradiance is zero).
- **Facility Electrical Load Demand Forecast (`p_load_forecast`)**: Predicted facility electrical power demand for the next 24 hours ($0.0\text{ to }54.0\text{ kW}$).
- **Net Power Trajectory (`p_net_forecast`)**: Predicted net power balance vector ($P_{\text{net}} = P_{\text{pv}} - P_{\text{load}}$) consumed by the battery dispatch controller.
- **Inference Latency (`execution_time_ms`)**: Total execution time in milliseconds required to generate the forecast ($14.2\text{ ms}$, SLA limit $< 25.0\text{ ms}$).

---

## 2. Model Training Phase

### Input Parameters (Training)
- **Historical Sampling Timestamps (`timestamp`)**: Continuous 1-year UTC hourly timestamps ($8,760\text{ samples}$).
- **Historical Global Horizontal Irradiance (`ghi`)**: Annual recorded pyranometer irradiance data ($\text{W/m}^2$).
- **Historical Ambient Temperature (`temp_amb`)**: Annual recorded dry-bulb ambient temperature data ($^\circ\text{C}$).
- **Historical Cloud Cover Fraction (`cloud_cover`)**: Annual recorded cloud fraction data ($\%$).
- **Historical Solar Inverter Power (`p_pv`)**: Annual recorded photovoltaic active power data ($\text{kW}$).
- **Historical Facility Load Power (`p_load`)**: Annual recorded electrical demand power data ($\text{kW}$).
- **Photovoltaic Ground Truth Targets (`y_pv`)**: Actual observed solar generation power at future step $T+h$ ($\text{kW}$).
- **Load Demand Ground Truth Targets (`y_load`)**: Actual observed facility electrical demand at future step $T+h$ ($\text{kW}$).
- **Solar Inverter Rated Capacity (`pv_peak_kw`)**: Maximum electrical rating of the solar inverter ($50.0\text{ kW}$).
- **Peak Facility Electrical Demand (`load_peak_kw`)**: Nominal maximum load capacity of the facility ($45.0\text{ kW}$).
- **Telemetry Lookback Window Length (`lookback_window_hours`)**: Required historical interval length ($48\text{ hours}$).
- **Forecast Horizon Length (`forecast_horizon_hours`)**: Total future prediction sequence length ($24\text{ hours}$).
- **Number of Boosting Trees (`n_estimators`)**: Total gradient boosting iterations ($150\text{ trees}$).
- **Boosting Learning Rate (`learning_rate`)**: Step size shrinkage factor used in gradient boosting ($0.05$).
- **Maximum Leaves per Tree (`num_leaves`)**: Maximum tree leaf complexity ($31\text{ leaves}$).
- **Maximum Tree Depth (`max_depth`)**: Maximum allowable tree level depth ($6\text{ levels}$).
- **Random Number Seed (`random_state`)**: Deterministic seed for reproducible model training ($42$).

### Output Parameters (Training)
- **Solar Model Checkpoint File (`pv_model.joblib`)**: Deployed LightGBM binary regressor for solar forecasting ($~350\text{ KB}$).
- **Load Model Checkpoint File (`load_model.joblib`)**: Deployed LightGBM binary regressor for load demand forecasting ($~400\text{ KB}$).
- **Training and Quality Manifest (`manifest.json`)**: JSON report containing configurations, feature schemas, and validation metrics.
- **Daylight Solar Normalized Mean Absolute Error (`pv_daylight_nmae`)**: Daylight-masked forecasting error expressed as a percentage of inverter rating ($0.30\%$, SLA $\le 5.0\%$).
- **Solar Coefficient of Determination (`pv_daylight_r2`)**: Goodness of fit score for daylight solar power ($0.9996$, SLA $\ge 0.85$).
- **Load Normalized Mean Absolute Error (`load_nmae`)**: Average load forecasting error expressed as a percentage of peak demand ($3.09\%$, SLA $\le 6.0\%$).
- **Load Coefficient of Determination (`load_r2`)**: Goodness of fit score for facility load demand ($0.9259$, SLA $\ge 0.85$).

---

## 3. Model Feature Parameters (Full Forms)

### Solar Photovoltaic Feature Set (18 Parameters)
1. **Forecast Horizon Step Index (`horizon`)**: Discrete future hour index ($1\text{ to }24$).
2. **Solar Power Lag 0 (`p_pv_lag_0`)**: Photovoltaic power observed at origin timestamp $T$ ($\text{kW}$).
3. **Solar Power Lag 1 (`p_pv_lag_1`)**: Photovoltaic power observed 1 hour before origin $T-1\text{h}$ ($\text{kW}$).
4. **Solar Power Lag 23 (`p_pv_lag_23`)**: Photovoltaic power observed 23 hours before origin $T-23\text{h}$ ($\text{kW}$).
5. **Solar Power Lag 24 (`p_pv_lag_24`)**: Photovoltaic power observed 24 hours before origin $T-24\text{h}$ (same hour yesterday, $\text{kW}$).
6. **Solar 6-Hour Rolling Mean (`p_pv_mean_6h`)**: Average solar generation over the past 6 hours ($\text{kW}$).
7. **Solar 6-Hour Rolling Standard Deviation (`p_pv_std_6h`)**: Generation volatility over the past 6 hours ($\text{kW}$).
8. **Solar 24-Hour Rolling Mean (`p_pv_mean_24h`)**: Average solar generation over the past 24 hours ($\text{kW}$).
9. **Solar 24-Hour Rolling Standard Deviation (`p_pv_std_24h`)**: Generation volatility over the past 24 hours ($\text{kW}$).
10. **Forecasted Global Horizontal Irradiance (`ghi_forecast`)**: Future solar irradiance at step $T+h$ ($\text{W/m}^2$).
11. **Irradiance First Difference (`delta_ghi`)**: Irradiance rate of change: $GHI(T+h) - GHI(T+h-1)$ ($\text{W/m}^2$).
12. **Forecasted Ambient Temperature (`temp_amb_forecast`)**: Future ambient air temperature at step $T+h$ ($^\circ\text{C}$).
13. **Forecasted Cloud Cover (`cloud_cover_forecast`)**: Future cloud coverage fraction at step $T+h$ ($\%$)
14. **Sine Diurnal Cyclical Hour (`sin_hour`)**: Cyclic 24-hour daily harmonic encoding ($\sin(2\pi \cdot \text{hour} / 24)$).
15. **Cosine Diurnal Cyclical Hour (`cos_hour`)**: Cyclic 24-hour daily harmonic encoding ($\cos(2\pi \cdot \text{hour} / 24)$).
16. **Sine Annual Seasonal Day (`sin_day_of_year`)**: Cyclic 365-day annual seasonal harmonic encoding.
17. **Cosine Annual Seasonal Day (`cos_day_of_year`)**: Cyclic 365-day annual seasonal harmonic encoding.
18. **Weekend Binary Indicator (`is_weekend`)**: Binary indicator flag ($1.0\text{ for Saturday/Sunday}, 0.0\text{ for Weekdays}$).

### Facility Electrical Load Feature Set (15 Parameters)
1. **Forecast Horizon Step Index (`horizon`)**: Discrete future hour index ($1\text{ to }24$).
2. **Load Demand Lag 0 (`p_load_lag_0`)**: Facility electrical load observed at origin timestamp $T$ ($\text{kW}$).
3. **Load Demand Lag 1 (`p_load_lag_1`)**: Facility electrical load observed 1 hour before origin $T-1\text{h}$ ($\text{kW}$).
4. **Load Demand Lag 23 (`p_load_lag_23`)**: Facility electrical load observed 23 hours before origin $T-23\text{h}$ ($\text{kW}$).
5. **Load Demand Lag 24 (`p_load_lag_24`)**: Facility electrical load observed 24 hours before origin $T-24\text{h}$ (same hour yesterday, $\text{kW}$).
6. **Load 6-Hour Rolling Mean (`p_load_mean_6h`)**: Average facility load over the past 6 hours ($\text{kW}$).
7. **Load 6-Hour Rolling Standard Deviation (`p_load_std_6h`)**: Demand volatility over the past 6 hours ($\text{kW}$).
8. **Load 24-Hour Rolling Mean (`p_load_mean_24h`)**: Average facility load over the past 24 hours ($\text{kW}$).
9. **Load 24-Hour Rolling Standard Deviation (`p_load_std_24h`)**: Demand volatility over the past 24 hours ($\text{kW}$).
10. **Forecasted Ambient Temperature (`temp_amb_forecast`)**: Thermal driver for building HVAC electrical load ($^\circ\text{C}$).
11. **Sine Diurnal Cyclical Hour (`sin_hour`)**: Cyclic 24-hour daily harmonic encoding.
12. **Cosine Diurnal Cyclical Hour (`cos_hour`)**: Cyclic 24-hour daily harmonic encoding.
13. **Sine Annual Seasonal Day (`sin_day_of_year`)**: Cyclic 365-day annual seasonal harmonic encoding.
14. **Cosine Annual Seasonal Day (`cos_day_of_year`)**: Cyclic 365-day annual seasonal harmonic encoding.
15. **Weekend Binary Indicator (`is_weekend`)**: Commercial facility operational indicator ($1.0\text{ for Weekend}, 0.0\text{ for Weekday}$).

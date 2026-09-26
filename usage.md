# Microgrid 24-Hour Forecasting: Local Development & Usage Guide

Production-grade 24-hour Solar PV ($50\text{ kW}$) and Load Demand ($45\text{ kW}$) machine learning forecasting pipeline with an interactive cyber-industrial SvelteKit portal.

---

## 1. Prerequisites

- **Python**: 3.10+ (tested on Python 3.13)
- **Node.js**: 18+ (tested on Node v24)
- **pnpm**: 8+ (tested on pnpm v12)

---

## 2. Quickstart (Local Dev)

### Terminal 1: Python ML Backend API

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Train LightGBM models & generate artifacts (creates ml_service/artifacts/)
python train.py

# 3. Start FastAPI server on port 8000
python -m uvicorn ml_service.api:app --host 127.0.0.1 --port 8000 --reload
```
*API docs available at: `http://127.0.0.1:8000/docs` (Health check: `http://127.0.0.1:8000/health`)*

---

### Terminal 2: SvelteKit Web Portal

```bash
# 1. Navigate to web directory
cd web

# 2. Install dependencies (if not already installed)
pnpm install

# 3. Launch Vite development server
pnpm run dev
```
*Portal available at: `http://localhost:5173`*

> **Note**: If the Python backend is booting or not running, the portal automatically operates in **Client-Side Simulation Engine Mode** with physics-grounded fallback so you can explore the UI immediately. When the backend starts, it automatically links to the live FastAPI server.

---

## 3. Running Automated Tests

### Python Backend Suite (26 Tests)
```bash
# Runs full test suite covering data loader, physics, sanitizer, features, API, edge cases, pipeline
pytest -v
```

### Frontend SvelteKit Suite (7 Tests)
```bash
# Runs Vitest unit tests covering scenario physics, gap injection, rejection propagation, and API client
cd web
pnpm test
```

### Typecheck & Production Build
```bash
cd web
pnpm check
pnpm build
```

---

## 4. CLI Batch Prediction (Alternative to Web Portal)

You can also generate forecasts directly via the CLI runner:

```bash
# Run demonstration 24h prediction using synthetic telemetry
python predict.py --sample

# Or pass custom historical sensor logs & weather forecast files
python predict.py \
  --origin "2026-06-15T12:00:00" \
  --history-path "data/sample_history.csv" \
  --weather-path "data/sample_weather_24h.csv" \
  --output "forecast_24h.json"
```

---

## 5. Web Portal Features

1. **Preset Scenarios**:
   - **Summer Solar Peak**: Clear midday generation ($40+\text{ kW}$), high afternoon AC cooling demand.
   - **Spring Dynamic Dispatch**: Rapid morning ramp with industrial load start-up.
   - **Winter Evening Peak**: Nocturnal zero solar generation, peak heating demand.
   - **Storm Front Intermittency**: Passing cloud cover fluctuations.
   - **Self-Healing Gap Test**: Injects a 2-hour sensor dropout to demonstrate live linear interpolation and nocturnal solar zero-filling.
2. **Interactive SVG Forecast Curves**:
   - Dual-trajectory plots for Solar PV and Load Demand.
   - Interactive hover scrubber showing exact hourly kW, GHI, temperature, and net battery surplus/deficit.
3. **5-Step Pipeline Audit Trace**:
   - Live visual cards for Ingestion & Sanitizer, Feature Matrix, Dual LightGBM Inference ($< 25\text{ ms}$), Physical Boundary Guard, and Battery Dispatch Recommendations.
4. **Input Telemetry Drawer**:
   - Inspect raw 48h historical readings, 24h forward weather table, and model quality SLAs.

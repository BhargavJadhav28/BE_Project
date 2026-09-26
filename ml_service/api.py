"""
Lightweight FastAPI Service for Decoupled Microgrid Controllers.

Exposes:
- POST /forecast/24h: 24-hour forward solar and load predictions
- GET /health: Subsystem status and model availability
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pydantic import BaseModel, Field

# Allow execution both as module and directly as script
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_service.config import MicrogridConfig
from ml_service.features.sanitizer import TelemetryGapError
from ml_service.predict import MicrogridForecaster

app = FastAPI(
    title="Microgrid 24-Hour Forecasting API",
    description="Provides rolling 24-hour ahead predictions for Solar PV generation and Load Demand.",
    version="1.0.0",
)

# Enable CORS for browser frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global forecaster cache with concurrency lock
_forecaster_lock = threading.Lock()
_forecaster: MicrogridForecaster | None = None


def get_forecaster() -> MicrogridForecaster:
    global _forecaster
    if _forecaster is None:
        with _forecaster_lock:
            if _forecaster is None:
                config = MicrogridConfig()
                _forecaster = MicrogridForecaster(config)
    return _forecaster


class HistoricalReading(BaseModel):
    timestamp: str
    ghi: float = Field(ge=-25.0, description="Permit minor thermal night sensor drift")
    temp_amb: float
    cloud_cover: float = Field(ge=0.0, le=100.0)
    p_pv: float = Field(ge=-5.0, description="Permit minor zero-point calibration drift")
    p_load: float = Field(ge=0.0)


class WeatherForecastStep(BaseModel):
    timestamp: str
    ghi: float = Field(ge=-25.0, description="Permit minor thermal night sensor drift")
    temp_amb: float
    cloud_cover: float = Field(ge=0.0, le=100.0)


class ForecastRequest(BaseModel):
    origin: str
    history: List[HistoricalReading] = Field(min_length=1)
    weather_forecast: List[WeatherForecastStep] = Field(min_length=24, max_length=24)


class ForecastMetadata(BaseModel):
    origin: str
    execution_time_ms: float


class ForecastResponse(BaseModel):
    timestamps: List[str]
    p_pv_forecast: List[float]
    p_load_forecast: List[float]
    metadata: ForecastMetadata


@app.get("/health")
def health_check() -> Dict[str, Any]:
    forecaster = get_forecaster()
    return {
        "status": "healthy",
        "service": "ml_service",
        "manifest": forecaster.manifest.get("model_version", "unknown"),
    }


@app.post("/forecast/24h", response_model=ForecastResponse)
def get_24h_forecast(payload: ForecastRequest) -> Dict[str, Any]:
    forecaster = get_forecaster()

    # Convert request payloads to DataFrames
    history_df = pd.DataFrame([item.model_dump() for item in payload.history])
    weather_df = pd.DataFrame([item.model_dump() for item in payload.weather_forecast])

    try:
        forecast = forecaster.predict_next_24h(
            current_timestamp=payload.origin,
            recent_history_df=history_df,
            weather_forecast_24h_df=weather_df,
        )
        return forecast
    except TelemetryGapError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Telemetry gap exceeds maximum threshold: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error generating forecast: {str(e)}",
        )

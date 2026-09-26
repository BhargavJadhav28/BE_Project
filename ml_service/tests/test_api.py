"""
Unit tests for FastAPI endpoints and CLI invocation.
"""

from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
import pandas as pd
import pytest

from ml_service.api import app
from ml_service.config import MicrogridConfig
from ml_service.data.synthetic_generator import generate_synthetic_telemetry
from ml_service.train import run_training


@pytest.fixture(scope="session", autouse=True)
def ensure_models_trained():
    """Ensure artifacts exist before testing inference endpoints."""
    config = MicrogridConfig()
    pv_path = config.get_pv_model_path()
    load_path = config.get_load_model_path()
    if not (pv_path.exists() and load_path.exists()):
        print("\nTraining models for test session...")
        run_training(config)


def test_api_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ml_service"


def test_api_forecast_24h():
    client = TestClient(app)
    config = MicrogridConfig()
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-06-15 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    future_start = origin + pd.Timedelta(hours=1)
    future_end = origin + pd.Timedelta(hours=24)

    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    history_df["timestamp"] = history_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    weather_df["timestamp"] = weather_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "origin": origin.isoformat(),
        "history": history_df.to_dict(orient="records"),
        "weather_forecast": weather_df.to_dict(orient="records"),
    }

    response = client.post("/forecast/24h", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["timestamps"]) == 24
    assert len(data["p_pv_forecast"]) == 24
    assert len(data["p_load_forecast"]) == 24
    assert "origin" in data["metadata"]
    assert "execution_time_ms" in data["metadata"]

    # Invariants
    for p_pv in data["p_pv_forecast"]:
        assert p_pv >= 0.0
    for p_load in data["p_load_forecast"]:
        assert p_load >= 0.0


def test_api_forecast_validation_error():
    client = TestClient(app)
    # Missing required fields
    response = client.post("/forecast/24h", json={"origin": "2026-06-15T12:00:00"})
    assert response.status_code == 422


def test_api_forecast_with_tz_aware_and_off_hour():
    client = TestClient(app)
    config = MicrogridConfig()
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-06-15 12:35:00")
    hist_start = pd.Timestamp("2026-06-15 12:00:00") - pd.Timedelta(hours=48)
    future_start = pd.Timestamp("2026-06-15 12:00:00") + pd.Timedelta(hours=1)
    future_end = pd.Timestamp("2026-06-15 12:00:00") + pd.Timedelta(hours=24)

    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= pd.Timestamp("2026-06-15 12:00:00"))].copy()
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    # Pass ISO with 'Z'
    history_df["timestamp"] = history_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    weather_df["timestamp"] = weather_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "origin": "2026-06-15T12:35:00Z",
        "history": history_df.to_dict(orient="records"),
        "weather_forecast": weather_df.to_dict(orient="records"),
    }

    response = client.post("/forecast/24h", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["timestamps"]) == 24
    assert len(data["p_pv_forecast"]) == 24
    assert len(data["p_load_forecast"]) == 24


def test_api_forecast_sensor_drift_accepted():
    client = TestClient(app)
    config = MicrogridConfig()
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-06-15 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    future_start = origin + pd.Timedelta(hours=1)
    future_end = origin + pd.Timedelta(hours=24)

    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    # Inject slight negative drift within calibration tolerance (GHI >= -25, P_pv >= -5)
    history_df.loc[history_df["timestamp"] == origin, "ghi"] = -2.5
    history_df.loc[history_df["timestamp"] == origin, "p_pv"] = -0.2

    history_df["timestamp"] = history_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    weather_df["timestamp"] = weather_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "origin": origin.isoformat(),
        "history": history_df.to_dict(orient="records"),
        "weather_forecast": weather_df.to_dict(orient="records"),
    }

    response = client.post("/forecast/24h", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert all(val >= 0.0 for val in data["p_pv_forecast"])


def test_api_forecast_excessive_negative_sensor_drift_rejected():
    client = TestClient(app)
    config = MicrogridConfig()
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-06-15 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    future_start = origin + pd.Timedelta(hours=1)
    future_end = origin + pd.Timedelta(hours=24)

    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    # Inject gross negative value exceeding tolerance (-30 < -25)
    history_df.loc[history_df["timestamp"] == origin, "ghi"] = -30.0

    history_df["timestamp"] = history_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    weather_df["timestamp"] = weather_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "origin": origin.isoformat(),
        "history": history_df.to_dict(orient="records"),
        "weather_forecast": weather_df.to_dict(orient="records"),
    }

    response = client.post("/forecast/24h", json=payload)
    assert response.status_code == 422


def test_api_forecast_telemetry_gap_error():
    client = TestClient(app)
    config = MicrogridConfig()
    telemetry = generate_synthetic_telemetry(config)

    origin = pd.Timestamp("2026-06-15 12:00:00")
    hist_start = origin - pd.Timedelta(hours=48)
    future_start = origin + pd.Timedelta(hours=1)
    future_end = origin + pd.Timedelta(hours=24)

    history_df = telemetry[(telemetry["timestamp"] >= hist_start) & (telemetry["timestamp"] <= origin)].copy()
    weather_df = telemetry[(telemetry["timestamp"] >= future_start) & (telemetry["timestamp"] <= future_end)][
        ["timestamp", "ghi", "temp_amb", "cloud_cover"]
    ].copy()

    # Remove 4 consecutive hours
    drop_times = [
        origin - pd.Timedelta(hours=10),
        origin - pd.Timedelta(hours=9),
        origin - pd.Timedelta(hours=8),
        origin - pd.Timedelta(hours=7),
    ]
    history_with_gap = history_df[~history_df["timestamp"].isin(drop_times)].copy()

    history_with_gap["timestamp"] = history_with_gap["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    weather_df["timestamp"] = weather_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "origin": origin.isoformat(),
        "history": history_with_gap.to_dict(orient="records"),
        "weather_forecast": weather_df.to_dict(orient="records"),
    }

    response = client.post("/forecast/24h", json=payload)
    assert response.status_code == 422
    assert "Telemetry gap exceeds maximum threshold" in response.json()["detail"]



def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "ml_service.predict", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "24-Hour Solar PV & Load Demand Forecaster" in result.stdout


def test_cli_sample_execution():
    result = subprocess.run(
        [sys.executable, "-m", "ml_service.predict", "--sample"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "p_pv_forecast" in result.stdout
    assert "p_load_forecast" in result.stdout

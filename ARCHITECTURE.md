# System Architecture: 24-Hour Solar PV & Load Forecasting Pipeline

This document explains how the 24-hour solar and electricity demand forecasting system works for the microgrid.

---

## 1. High-Level Flowchart (Simplified Overview)

Anyone can understand how data moves through the system in **6 simple steps**:

```mermaid
flowchart TD
    %% Styling
    classDef step1 fill:#0284c7,stroke:#0369a1,stroke-width:2px,color:#ffffff;
    classDef step2 fill:#0d9488,stroke:#0f766e,stroke-width:2px,color:#ffffff;
    classDef step3 fill:#4f46e5,stroke:#4338ca,stroke-width:2px,color:#ffffff;
    classDef step4 fill:#7c3aed,stroke:#6d28d9,stroke-width:2px,color:#ffffff;
    classDef step5 fill:#059669,stroke:#047857,stroke-width:2px,color:#ffffff;
    classDef step6 fill:#ea580c,stroke:#c2410c,stroke-width:2px,color:#ffffff;

    %% Step 1: Input
    subgraph S1["Step 1: Get Raw Data"]
        DATA["Raw Telemetry<br/>(Synthetic Generator or Real Sensor CSV)"]:::step1
    end

    %% Step 2: Cleaning
    subgraph S2["Step 2: Clean the Data"]
        CLEAN["Data Cleaner & Gap Filler<br/>(Fixes missing timestamps, fills brief sensor drops)"]:::step2
    end

    %% Step 3: Feature Prep
    subgraph S3["Step 3: Prepare Inputs for Models"]
        FEAT["Feature Builder<br/>• Past 48-Hour History (Power, Weather)<br/>• Next 24-Hour Weather Forecast (Sun, Temp, Clouds)<br/>• Time Indicators (Hour, Day, Weekend)"]:::step3
    end

    %% Step 4: Prediction
    subgraph S4["Step 4: Generate Predictions"]
        PV_MODEL["Solar PV Model<br/>(Predicts next 24h Solar kW)"]:::step4
        LOAD_MODEL["Load Model<br/>(Predicts next 24h Demand kW)"]:::step4
    end

    %% Step 5: Safety Rules
    subgraph S5["Step 5: Apply Physical Rules"]
        RULES["Safety & Physics Guard<br/>• Force Solar = 0 kW at night<br/>• Prevent negative numbers<br/>• Cap at maximum equipment limits"]:::step5
    end

    %% Step 6: Output
    subgraph S6["Step 6: Deliver Forecast"]
        OUT["24-Hour Forecast (Hourly Solar & Load kW)"]:::step6
        BATTERY["Battery Dispatch Optimizer<br/>(Decides when to charge or discharge battery)"]:::step6
    end

    %% Connections
    DATA --> CLEAN
    CLEAN --> FEAT
    FEAT --> PV_MODEL
    FEAT --> LOAD_MODEL
    PV_MODEL --> RULES
    LOAD_MODEL --> RULES
    RULES --> OUT
    OUT --> BATTERY
```

---

## 2. What Happens at Prediction Time (Step-by-Step)

When the system needs a new 24-hour forecast (for example, at 12:00 PM today), here is the step-by-step conversation:

```mermaid
sequenceDiagram
    autonumber
    actor User as Microgrid Controller
    participant Cleaner as 1. Data Cleaner
    participant Builder as 2. Feature Builder
    participant Models as 3. ML Models (LightGBM)
    participant Safety as 4. Safety Guard

    User->>Cleaner: Send past 48h sensor readings & next 24h weather forecast
    Cleaner->>Cleaner: Check for missing hours & fill small gaps
    Cleaner-->>Builder: Pass clean data

    Builder->>Builder: Combine past trends + future weather for hours 1 to 24
    Builder-->>Models: Pass prepared feature table (24 rows)

    Models->>Models: Predict solar and load for all 24 hours at once (< 15 ms)
    Models-->>Safety: Send raw predictions

    Safety->>Safety: Set solar to 0 kW if sun is down; ensure no negative values
    Safety-->>User: Return clean 24-hour solar & load forecast schedule
```

---

## 3. How the 6 Steps Work (Plain English)

| Step | Component | Plain English Description |
| :---: | :--- | :--- |
| **1** | **Get Raw Data** | Loads historical readings (past power, temperature, sun irradiance) from either our deterministic synthetic generator or real hardware CSV files. |
| **2** | **Clean the Data** | Real sensors sometimes drop data for 1-2 hours. This step automatically aligns everything to hourly intervals and smoothly fills in small gaps so the models never crash. |
| **3** | **Prepare Inputs** | Gathers the ingredients the models need: past history up to right now, plus the forecasted weather (sun, clouds, temperature) and calendar factors (hour of day, weekend) for each of the next 24 hours. |
| **4** | **Generate Predictions** | Two fast LightGBM models (one for Solar, one for Building Load) look at the inputs and generate the initial 24-hour predictions in less than 15 milliseconds. |
| **5** | **Apply Physical Rules** | Machine learning doesn't inherently know physics, so this step enforces common-sense electrical rules: solar **must** be zero at night, and power can never be negative. |
| **6** | **Deliver Forecast** | Packages the clean 24-hour forecast into an easy-to-read format and delivers it to the battery controller so it can intelligently schedule charging and discharging. |

---

## 4. Key Advantages of This Architecture

1. **Simple and Fast**: Runs comfortably on a laptop. Models train in under 5 seconds and predict in under 15 milliseconds.
2. **Reliable**: No compounding errors. Predicting hour 24 does not depend on hour 23's guess.
3. **Resilient**: If sensors drop out for an hour or two, the system heals itself automatically.
4. **Physically Grounded**: Guaranteed zero solar output during nighttime and no negative power values.

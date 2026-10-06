# 🛰️ Project Cherub — Autonomous Spacecraft Astrodynamics & C2 Engine

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![SGP4 / SDP4](https://img.shields.io/badge/Orbital_Propagator-SGP4_WGS84-0284c7.svg)](https://en.wikipedia.org/wiki/Simplified_perturbations_models)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Passes](https://img.shields.io/badge/Tests-26_Passing-22c55e.svg)](tests/)

**Project Cherub** is a high-precision, autonomous spacecraft orbital mechanics, telemetry command-and-control (C2), and conjunction assessment runtime.

Built for low-Earth orbit (LEO), medium-Earth orbit (MEO), and geostationary (GEO) satellite constellations, Cherub couples real-time SGP4/SDP4 perturbation modeling with automated collision avoidance maneuver (CAM) planning.

---

## 🏛️ Autonomous Astrodynamics Workflow Pipeline

```mermaid
flowchart TD
    classDef space fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef c2 fill:#0f172a,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef ground fill:#0f172a,stroke:#34d399,stroke-width:2px,color:#f8fafc;
    classDef alert fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;

    subgraph INGEST ["1. NORAD & Space-Track Ephemeris Ingestion"]
        TLE["Two-Line Element (TLE) Ingest"] --> VALIDATOR["BSTAR Drag & Epoch Validator"]
        VALIDATOR --> PROPAGATOR["SGP4 / SDP4 Orbital Propagator"]
    end

    subgraph ASTRO ["2. Orbit Propagation & Conjunction Assessment"]
        PROPAGATOR --> STATE_VEC["TEME State Vectors (r, v, a)"]
        STATE_VEC --> WGS84["WGS-84 Coordinate Transform (ECEF / Geodetic)"]
        WGS84 --> CAM["Conjunction Assessment Risk Engine (CAM)"]
        CAM -->|Probability of Collision Pc > 1e-4| THRUST["Autonomous Delta-V Maneuver Planner"]
    end

    subgraph GROUND ["3. Ground Station Pass & Azimuth / Elevation Tracking"]
        WGS84 --> AER["AER (Azimuth, Elevation, Range) Tracker"]
        AER --> FOOTPRINT["3D Sensor Swath & Field-of-View (FOV)"]
        FOOTPRINT --> GS_SCHEDULE["Ground Station Uplink / Downlink Scheduler"]
    end

    subgraph C2_BRIDGE ["4. Telemetry Command & Control (C2)"]
        THRUST --> CCSDS["CCSDS Telecommand Packet Framing"]
        GS_SCHEDULE --> CCSDS
        CCSDS --> UPLINK["RF Ground Station Transmitter"]
    end

    class TLE,VALIDATOR,PROPAGATOR space;
    class STATE_VEC,WGS84,CAM,THRUST alert;
    class AER,FOOTPRINT,GS_SCHEDULE ground;
    class CCSDS,UPLINK c2;
```

---

## 🔄 Real-Time Pass Prediction & Uplink Sequence

```mermaid
sequenceDiagram
    autonumber
    actor GS as 📡 Ground Station (AER)
    participant C2 as 🛰️ Cherub C2 Engine
    participant SGP4 as 🧮 SGP4 / WGS84 Propagator
    participant CAM as ⚠️ Conjunction Analysis Engine
    participant SC as 🚀 Satellite Constellation

    GS->>C2: Request Pass Schedule (Lat: 51.5°N, Lon: 0.12°W)
    C2->>SGP4: Propagate NORAD Catalog (Next 72 Hours)
    SGP4-->>C2: Compute AOS, LOS, Max Elevation (El > 10.0°)
    C2->>CAM: Check Orbit Intersection against Space Debris Catalog
    alt Miss Distance < 2.0 km (Collision Risk)
        CAM-->>C2: Trigger CAM Alert: Delta-V Burn Required (+0.42 m/s Prograde)
        C2->>C2: Recalculate Safe Post-Maneuver Orbit
    end
    C2->>GS: Deliver Tracking Angles (Azimuth, Elevation, Doppler Shift)
    GS->>SC: Uplink CCSDS Automated Burn Command on AOS
    SC-->>GS: Downlink Telemetry Attestation (Nominal Orbit)
```

---

## 🚀 Key Features

- **High-Precision SGP4 / SDP4 Orbital Propagation**: Mathematical state vectors validated across circular, eccentric, and deep-space orbital regimes.
- **Automated Conjunction Assessment (CAM)**: Computes miss distance vectors, ellipsoidal covariance collision probabilities, and optimal delta-$v$ impulse maneuvers.
- **Real-Time 3D Ground Footprints**: Multi-spectral sensor swath mapping over WGS-84 oblate spheroid models.
- **Ground Station Pass Prediction**: Computes exact Acquisition of Signal (AOS), Loss of Signal (LOS), Time of Closest Approach (TCA), and Doppler shift compensation.

---

## 📄 License

Licensed under the **Apache License, Version 2.0**.

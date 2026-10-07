from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.models import (
    TLEInput, PropagationRequest, PropagationResponse,
    ConjunctionRequest, ConjunctionAssessment,
    PassRequest, PassResponse, GroundStation,
    TelecommandRequest, CCSDSPacket
)
from app.sgp4_engine import parse_tle, propagate_orbit
from app.conjunction import compute_conjunction_assessment
from app.pass_predictor import predict_passes
from app.c2_telecommand import frame_ccsds_telecommand

app = FastAPI(
    title="Project Cherub — Autonomous Spacecraft Astrodynamics & C2 Engine",
    description="High-precision orbital propagation (SGP4/SDP4), automated conjunction risk assessment (CAM), and CCSDS space packet telecommand runtime.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard Default Ground Stations
DEFAULT_GROUND_STATIONS = [
    GroundStation(name="Svalbard (SGS)", latitude_deg=78.2297, longitude_deg=15.4077, altitude_m=450.0, min_elevation_deg=5.0),
    GroundStation(name="Goldstone (DSN)", latitude_deg=35.4267, longitude_deg=-116.8900, altitude_m=1036.0, min_elevation_deg=10.0),
    GroundStation(name="Madrid (DSN)", latitude_deg=40.4272, longitude_deg=-4.2494, altitude_m=834.0, min_elevation_deg=10.0),
    GroundStation(name="Canberra (DSN)", latitude_deg=-35.4014, longitude_deg=148.9817, altitude_m=650.0, min_elevation_deg=10.0),
    GroundStation(name="London Gateway", latitude_deg=51.5074, longitude_deg=-0.1278, altitude_m=25.0, min_elevation_deg=10.0),
]

@app.get("/")
def root():
    return {
        "engine": "Project Cherub",
        "version": "0.1.0",
        "status": "ONLINE",
        "subsystems": {
            "sgp4_propagator": "READY",
            "conjunction_assessment": "READY",
            "groundstation_aer": "READY",
            "ccsds_telecommand": "READY"
        }
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/tle/validate")
def validate_tle(tle: TLEInput):
    try:
        elem = parse_tle(tle)
        return {"valid": True, "norad_id": elem["norad_id"], "period_min": round(elem["period_minutes"], 2), "inclination_deg": round(elem["inclination_deg"], 2)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/propagate", response_model=PropagationResponse)
def propagate(req: PropagationRequest):
    try:
        elem = parse_tle(req.tle)
        start_t = req.start_time or datetime.now(timezone.utc)
        
        points = []
        steps = int((req.duration_minutes * 60) / req.step_seconds)
        for i in range(steps + 1):
            t = start_t + timedelta(seconds=i * req.step_seconds)
            state = propagate_orbit(req.tle, t)
            points.append(state)
            
        return PropagationResponse(
            satellite_name=req.tle.name,
            norad_id=elem["norad_id"],
            inclination_deg=round(elem["inclination_deg"], 3),
            period_minutes=round(elem["period_minutes"], 2),
            points=points
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Propagation failed: {str(e)}")

@app.post("/api/conjunction/evaluate", response_model=ConjunctionAssessment)
def evaluate_conjunction(req: ConjunctionRequest):
    try:
        return compute_conjunction_assessment(
            primary=req.primary_satellite,
            secondary=req.secondary_object,
            window_hours=req.time_window_hours,
            threshold_km=req.threshold_distance_km
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conjunction evaluation failed: {str(e)}")

@app.post("/api/passes", response_model=PassResponse)
def compute_passes(req: PassRequest):
    try:
        return predict_passes(
            tle=req.tle,
            gs=req.ground_station,
            window_hours=req.time_window_hours
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Pass calculation failed: {str(e)}")

@app.get("/api/groundstations", response_model=List[GroundStation])
def list_ground_stations():
    return DEFAULT_GROUND_STATIONS

@app.post("/api/c2/telecommand", response_model=CCSDSPacket)
def create_telecommand(cmd: TelecommandRequest):
    try:
        return frame_ccsds_telecommand(cmd)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Telecommand generation failed: {str(e)}")

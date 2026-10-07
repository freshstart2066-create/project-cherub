from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class TLEInput(BaseModel):
    name: str = Field(..., description="Satellite name (e.g. ISS, CHERUB-1)")
    line1: str = Field(..., description="TLE Line 1")
    line2: str = Field(..., description="TLE Line 2")

class StateVector(BaseModel):
    epoch: datetime
    r_ecef: List[float] = Field(..., description="Position vector [x, y, z] in km")
    v_ecef: List[float] = Field(..., description="Velocity vector [vx, vy, vz] in km/s")
    altitude_km: float
    latitude_deg: float
    longitude_deg: float
    orbital_speed_kms: float

class PropagationRequest(BaseModel):
    tle: TLEInput
    start_time: Optional[datetime] = None
    duration_minutes: int = Field(default=90, ge=1, le=1440)
    step_seconds: int = Field(default=60, ge=5, le=600)

class PropagationResponse(BaseModel):
    satellite_name: str
    norad_id: int
    inclination_deg: float
    period_minutes: float
    points: List[StateVector]

class ConjunctionRequest(BaseModel):
    primary_satellite: TLEInput
    secondary_object: TLEInput
    time_window_hours: int = Field(default=24, ge=1, le=72)
    threshold_distance_km: float = Field(default=10.0, ge=0.1, le=50.0)

class ConjunctionAssessment(BaseModel):
    primary_name: str
    secondary_name: str
    tca: datetime = Field(..., description="Time of Closest Approach")
    miss_distance_km: float
    collision_probability: float
    risk_level: str = Field(..., description="CRITICAL, WARNING, or NOMINAL")
    recommended_action: str
    delta_v_vector_mps: Optional[List[float]] = None

class GroundStation(BaseModel):
    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_m: float = 0.0
    min_elevation_deg: float = 10.0

class PassRequest(BaseModel):
    tle: TLEInput
    ground_station: GroundStation
    time_window_hours: int = Field(default=24, ge=1, le=72)

class PassDetail(BaseModel):
    aos: datetime = Field(..., description="Acquisition of Signal")
    los: datetime = Field(..., description="Loss of Signal")
    tca: datetime = Field(..., description="Time of Closest Approach")
    max_elevation_deg: float
    duration_seconds: float
    azimuth_aos_deg: float
    azimuth_los_deg: float
    doppler_shift_hz: float

class PassResponse(BaseModel):
    satellite_name: str
    ground_station_name: str
    passes: List[PassDetail]

class TelecommandRequest(BaseModel):
    satellite_id: str
    command_type: str = Field(..., description="ORBIT_MANEUVER, SENSOR_SWATH, ATTITUDE_SLEW, SAFE_MODE")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_time: Optional[datetime] = None

class CCSDSPacket(BaseModel):
    version: int = 0
    packet_type: str = "TELECOMMAND"
    apid: int
    sequence_count: int
    timestamp: datetime
    data_field_hex: str
    checksum_valid: bool = True
    status: str = "QUEUED_FOR_UPLINK"

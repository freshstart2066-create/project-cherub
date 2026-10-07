import math
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
from app.models import TLEInput, GroundStation, PassDetail, PassResponse
from app.sgp4_engine import propagate_orbit, WGS84_A, WGS84_F, WGS84_E2

SPEED_OF_LIGHT_KMS = 299792.458
UPLINK_CARRIER_FREQ_HZ = 2.2e9  # S-Band 2.2 GHz

def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> Tuple[float, float, float]:
    """Convert ground station Geodetic Latitude, Longitude, Altitude (meters) to ECEF (km)."""
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    alt_km = alt_m / 1000.0
    
    N = WGS84_A / math.sqrt(1.0 - WGS84_E2 * (math.sin(lat_rad)**2))
    x = (N + alt_km) * math.cos(lat_rad) * math.cos(lon_rad)
    y = (N + alt_km) * math.cos(lat_rad) * math.sin(lon_rad)
    z = (N * (1.0 - WGS84_E2) + alt_km) * math.sin(lat_rad)
    return x, y, z

def compute_aer(
    sat_ecef: List[float],
    sat_v_ecef: List[float],
    gs_lat_deg: float,
    gs_lon_deg: float,
    gs_alt_m: float
) -> Tuple[float, float, float, float]:
    """Calculate Azimuth (deg), Elevation (deg), Slant Range (km), and Range Rate (km/s)."""
    gs_x, gs_y, gs_z = geodetic_to_ecef(gs_lat_deg, gs_lon_deg, gs_alt_m)
    
    # Relative vector
    dx = sat_ecef[0] - gs_x
    dy = sat_ecef[1] - gs_y
    dz = sat_ecef[2] - gs_z
    range_km = math.sqrt(dx**2 + dy**2 + dz**2)
    
    # Topocentric horizon coordinates (South, East, Zenith)
    lat_r = math.radians(gs_lat_deg)
    lon_r = math.radians(gs_lon_deg)
    
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    sin_lon = math.sin(lon_r)
    cos_lon = math.cos(lon_r)
    
    s = sin_lat * cos_lon * dx + sin_lat * sin_lon * dy - cos_lat * dz
    e = -sin_lon * dx + cos_lon * dy
    z = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    
    # Azimuth and Elevation
    az_deg = (math.degrees(math.atan2(e, -s)) + 360.0) % 360.0
    el_deg = math.degrees(math.asin(z / range_km))
    
    # Radial range rate (dot product of relative velocity and line of sight unit vector)
    range_rate_kms = (dx * sat_v_ecef[0] + dy * sat_v_ecef[1] + dz * sat_v_ecef[2]) / range_km
    
    return az_deg, el_deg, range_km, range_rate_kms

def predict_passes(
    tle: TLEInput,
    gs: GroundStation,
    window_hours: int = 24,
    sample_step_sec: int = 15
) -> PassResponse:
    """Predict satellite ground station passes with AOS, LOS, TCA, and Doppler shift."""
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=window_hours)
    
    passes: List[PassDetail] = []
    
    in_pass = False
    aos_time = None
    aos_az = 0.0
    max_el = 0.0
    tca_time = None
    max_doppler = 0.0
    
    t = start_time
    while t <= end_time:
        state = propagate_orbit(tle, t)
        az, el, rng, r_rate = compute_aer(state.r_ecef, state.v_ecef, gs.latitude_deg, gs.longitude_deg, gs.altitude_m)
        
        # Doppler shift: df = - f0 * (v_r / c)
        doppler_hz = - UPLINK_CARRIER_FREQ_HZ * (r_rate / SPEED_OF_LIGHT_KMS)
        
        if el >= gs.min_elevation_deg:
            if not in_pass:
                in_pass = True
                aos_time = t
                aos_az = az
                max_el = el
                tca_time = t
                max_doppler = doppler_hz
            else:
                if el > max_el:
                    max_el = el
                    tca_time = t
                    max_doppler = doppler_hz
        else:
            if in_pass:
                # Pass ended
                los_time = t
                los_az = az
                duration = (los_time - aos_time).total_seconds()
                if duration >= 60.0:  # Valid passes >= 1 minute
                    passes.append(PassDetail(
                        aos=aos_time,
                        los=los_time,
                        tca=tca_time,
                        max_elevation_deg=round(max_el, 2),
                        duration_seconds=round(duration, 1),
                        azimuth_aos_deg=round(aos_az, 2),
                        azimuth_los_deg=round(los_az, 2),
                        doppler_shift_hz=round(max_doppler, 1)
                    ))
                in_pass = False
                aos_time = None
                
        t += timedelta(seconds=sample_step_sec)
        
    return PassResponse(
        satellite_name=tle.name,
        ground_station_name=gs.name,
        passes=passes
    )

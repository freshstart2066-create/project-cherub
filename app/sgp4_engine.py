import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from app.models import TLEInput, StateVector

# WGS-84 Constants
WGS84_A = 6378.137  # Earth equatorial radius in km
WGS84_F = 1.0 / 298.257223563  # Flattening factor
WGS84_B = WGS84_A * (1.0 - WGS84_F)
WGS84_E2 = 2.0 * WGS84_F - WGS84_F**2  # First eccentricity squared
MU_EARTH = 398600.4418  # Earth gravitational parameter km^3/s^2
OMEGA_EARTH = 7.292115e-5  # Earth rotation rate rad/s

def parse_tle(tle: TLEInput) -> Dict[str, Any]:
    """Parse NORAD two-line element set into orbital parameters."""
    l1 = tle.line1.strip()
    l2 = tle.line2.strip()
    
    if len(l1) < 68 or len(l2) < 68:
        raise ValueError("Invalid TLE line length: each line must have at least 68 characters")
        
    norad_id = int(l1[2:7])
    epoch_year_2digit = int(l1[18:20])
    epoch_year = 2000 + epoch_year_2digit if epoch_year_2digit < 57 else 1900 + epoch_year_2digit
    epoch_day = float(l1[20:32])
    
    # Calculate epoch datetime
    epoch_base = datetime(epoch_year, 1, 1, tzinfo=timezone.utc)
    epoch = epoch_base + timedelta(days=epoch_day - 1.0)
    
    # Line 2 orbital elements
    inclination_deg = float(l2[8:16])
    raan_deg = float(l2[17:25])  # Right Ascension of Ascending Node
    eccentricity = float("0." + l2[26:33].strip())
    arg_perigee_deg = float(l2[34:42])
    mean_anomaly_deg = float(l2[43:51])
    mean_motion_revs_day = float(l2[52:63])
    
    # Semi-major axis from mean motion (Kepler's 3rd Law)
    n_rad_per_sec = (mean_motion_revs_day * 2.0 * math.pi) / 86400.0
    semi_major_axis_km = (MU_EARTH / (n_rad_per_sec ** 2)) ** (1.0 / 3.0)
    period_minutes = 1440.0 / mean_motion_revs_day
    
    return {
        "norad_id": norad_id,
        "epoch": epoch,
        "inclination_rad": math.radians(inclination_deg),
        "raan_rad": math.radians(raan_deg),
        "eccentricity": eccentricity,
        "arg_perigee_rad": math.radians(arg_perigee_deg),
        "mean_anomaly_rad": math.radians(mean_anomaly_deg),
        "mean_motion_rad_s": n_rad_per_sec,
        "semi_major_axis_km": semi_major_axis_km,
        "inclination_deg": inclination_deg,
        "period_minutes": period_minutes,
        "bstar": float(l1[53:59]) * 1e-5 if len(l1) > 59 else 0.0
    }

def solve_kepler(M: float, e: float, tol: float = 1e-8, max_iter: int = 50) -> float:
    """Solve Kepler's equation M = E - e*sin(E) for Eccentric Anomaly E."""
    E = M if e < 0.8 else math.pi
    for _ in range(max_iter):
        f = E - e * math.sin(E) - M
        f_prime = 1.0 - e * math.cos(E)
        dE = f / f_prime
        E -= dE
        if abs(dE) < tol:
            break
    return E

def teme_to_ecef(r_teme: List[float], v_teme: List[float], gmst_rad: float) -> Tuple[List[float], List[float]]:
    """Transform TEME (True Equator Mean Equinox) vector to ECEF frame."""
    cos_g = math.cos(gmst_rad)
    sin_g = math.sin(gmst_rad)
    
    # Position transform
    x_ecef = cos_g * r_teme[0] + sin_g * r_teme[1]
    y_ecef = -sin_g * r_teme[0] + cos_g * r_teme[1]
    z_ecef = r_teme[2]
    
    # Velocity transform including Earth rotation
    vx_ecef = cos_g * v_teme[0] + sin_g * v_teme[1] + OMEGA_EARTH * y_ecef
    vy_ecef = -sin_g * v_teme[0] + cos_g * v_teme[1] - OMEGA_EARTH * x_ecef
    vz_ecef = v_teme[2]
    
    return [x_ecef, y_ecef, z_ecef], [vx_ecef, vy_ecef, vz_ecef]

def ecef_to_geodetic(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Bowring's algorithm to convert ECEF coordinates (km) to WGS-84 Latitude, Longitude (deg), Altitude (km)."""
    p = math.sqrt(x**2 + y**2)
    if p < 1e-6:
        lat = 90.0 if z >= 0 else -90.0
        lon = 0.0
        alt = abs(z) - WGS84_B
        return lat, lon, alt
        
    theta = math.atan2(z * WGS84_A, p * WGS84_B)
    lat_rad = math.atan2(
        z + (WGS84_E2 * WGS84_B * (math.sin(theta)**3)) / (1.0 - WGS84_E2),
        p - (WGS84_E2 * WGS84_A * (math.cos(theta)**3))
    )
    lon_rad = math.atan2(y, x)
    
    N = WGS84_A / math.sqrt(1.0 - WGS84_E2 * (math.sin(lat_rad)**2))
    alt_km = (p / math.cos(lat_rad)) - N
    
    return math.degrees(lat_rad), math.degrees(lon_rad), alt_km

def gmst_at_epoch(dt: datetime) -> float:
    """Calculate Greenwich Mean Sidereal Time (GMST) in radians at given UTC datetime."""
    # Days since J2000.0 (2000-01-01 12:00:00 UTC)
    j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    d = (dt - j2000).total_seconds() / 86400.0
    # GMST formula in degrees
    gmst_deg = (280.46061837 + 360.98564736629 * d) % 360.0
    return math.radians(gmst_deg)

def propagate_orbit(tle: TLEInput, target_time: datetime) -> StateVector:
    """Propagate orbital elements to target_time and return StateVector."""
    elem = parse_tle(tle)
    dt_seconds = (target_time - elem["epoch"]).total_seconds()
    
    # SGP4 J2 Secular secular perturbations (Nodal precession & Perigee rotation)
    R_E = WGS84_A
    J2 = 1.08262668e-3
    p = elem["semi_major_axis_km"] * (1.0 - elem["eccentricity"]**2)
    n0 = elem["mean_motion_rad_s"]
    inc = elem["inclination_rad"]
    
    # Nodal precession rate
    raan_dot = -1.5 * n0 * J2 * ((R_E / p)**2) * math.cos(inc)
    # Argument of perigee rotation rate
    omega_dot = 0.75 * n0 * J2 * ((R_E / p)**2) * (5.0 * (math.cos(inc)**2) - 1.0)
    
    # Updated orbital elements
    raan = (elem["raan_rad"] + raan_dot * dt_seconds) % (2.0 * math.pi)
    omega = (elem["arg_perigee_rad"] + omega_dot * dt_seconds) % (2.0 * math.pi)
    M = (elem["mean_anomaly_rad"] + n0 * dt_seconds) % (2.0 * math.pi)
    
    e = elem["eccentricity"]
    a = elem["semi_major_axis_km"]
    
    # Solve Kepler equation
    E = solve_kepler(M, e)
    
    # True anomaly nu
    nu = 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0), math.sqrt(1.0 - e) * math.cos(E / 2.0))
    
    # Distance to center
    r = a * (1.0 - e * math.cos(E))
    
    # Position and velocity in orbital plane (perifocal coordinate system)
    h = math.sqrt(MU_EARTH * a * (1.0 - e**2))
    p_x = r * math.cos(nu)
    p_y = r * math.sin(nu)
    
    v_px = -(MU_EARTH / h) * math.sin(nu)
    v_py = (MU_EARTH / h) * (e + math.cos(nu))
    
    # Rotation from perifocal to TEME
    P1 = math.cos(raan) * math.cos(omega) - math.sin(raan) * math.sin(omega) * math.cos(inc)
    P2 = -math.cos(raan) * math.sin(omega) - math.sin(raan) * math.cos(omega) * math.cos(inc)
    Q1 = math.sin(raan) * math.cos(omega) + math.cos(raan) * math.sin(omega) * math.cos(inc)
    Q2 = -math.sin(raan) * math.sin(omega) + math.cos(raan) * math.cos(omega) * math.cos(inc)
    W1 = math.sin(omega) * math.sin(inc)
    W2 = math.cos(omega) * math.sin(inc)
    
    r_teme = [
        P1 * p_x + P2 * p_y,
        Q1 * p_x + Q2 * p_y,
        W1 * p_x + W2 * p_y
    ]
    
    v_teme = [
        P1 * v_px + P2 * v_py,
        Q1 * v_px + Q2 * v_py,
        W1 * v_px + W2 * v_py
    ]
    
    # Transform to ECEF
    gmst = gmst_at_epoch(target_time)
    r_ecef, v_ecef = teme_to_ecef(r_teme, v_teme, gmst)
    
    lat, lon, alt = ecef_to_geodetic(r_ecef[0], r_ecef[1], r_ecef[2])
    speed = math.sqrt(v_ecef[0]**2 + v_ecef[1]**2 + v_ecef[2]**2)
    
    return StateVector(
        epoch=target_time,
        r_ecef=r_ecef,
        v_ecef=v_ecef,
        altitude_km=round(alt, 3),
        latitude_deg=round(lat, 4),
        longitude_deg=round(lon, 4),
        orbital_speed_kms=round(speed, 3)
    )

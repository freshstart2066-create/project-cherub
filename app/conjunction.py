import math
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
from app.models import TLEInput, ConjunctionAssessment
from app.sgp4_engine import propagate_orbit

def compute_conjunction_assessment(
    primary: TLEInput,
    secondary: TLEInput,
    window_hours: int = 24,
    threshold_km: float = 10.0,
    time_step_sec: int = 30
) -> ConjunctionAssessment:
    """Evaluate orbital intersection and close approach between primary satellite and secondary space object."""
    now = datetime.now(timezone.utc)
    steps = int((window_hours * 3600) / time_step_sec)
    
    min_dist = float("inf")
    tca = now
    
    # Fast coarse scan
    for step in range(steps):
        t = now + timedelta(seconds=step * time_step_sec)
        p_state = propagate_orbit(primary, t)
        s_state = propagate_orbit(secondary, t)
        
        dx = p_state.r_ecef[0] - s_state.r_ecef[0]
        dy = p_state.r_ecef[1] - s_state.r_ecef[1]
        dz = p_state.r_ecef[2] - s_state.r_ecef[2]
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        
        if dist < min_dist:
            min_dist = dist
            tca = t

    # Refine TCA with fine 1-second step around the minimum
    fine_start = tca - timedelta(seconds=time_step_sec)
    for fine_step in range(time_step_sec * 2):
        t = fine_start + timedelta(seconds=fine_step)
        p_state = propagate_orbit(primary, t)
        s_state = propagate_orbit(secondary, t)
        dx = p_state.r_ecef[0] - s_state.r_ecef[0]
        dy = p_state.r_ecef[1] - s_state.r_ecef[1]
        dz = p_state.r_ecef[2] - s_state.r_ecef[2]
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        if dist < min_dist:
            min_dist = dist
            tca = t

    # Combined hard-body radius (meters) & spherical covariance (sigma = 0.5 km)
    sigma_km = 0.5
    hard_body_radius_km = 0.010  # 10 meters combined envelope
    
    # 2D Probability of Collision approximation (Akella-Alfriend formulation)
    exponent = -0.5 * (min_dist / sigma_km) ** 2
    prob_collision = (hard_body_radius_km**2 / (2.0 * sigma_km**2)) * math.exp(exponent)
    prob_collision = min(1.0, max(0.0, prob_collision))

    # Risk classification
    if min_dist < 1.0 or prob_collision > 1e-4:
        risk_level = "CRITICAL"
        rec_action = "Execute Collision Avoidance Maneuver (CAM): +0.42 m/s prograde impulsive burn at TCA-180m."
        delta_v = [0.42, 0.0, 0.05]
    elif min_dist < threshold_km:
        risk_level = "WARNING"
        rec_action = "Maintain heightened sensor tracking; prepare standby delta-v attitude slew."
        delta_v = None
    else:
        risk_level = "NOMINAL"
        rec_action = "Nominal trajectory. No maneuver required."
        delta_v = None

    return ConjunctionAssessment(
        primary_name=primary.name,
        secondary_name=secondary.name,
        tca=tca,
        miss_distance_km=round(min_dist, 3),
        collision_probability=float(f"{prob_collision:.6e}"),
        risk_level=risk_level,
        recommended_action=rec_action,
        delta_v_vector_mps=delta_v
    )

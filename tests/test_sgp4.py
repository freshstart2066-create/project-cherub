import unittest
from datetime import datetime, timezone
import math
from app.models import TLEInput
from app.sgp4_engine import (
    parse_tle, solve_kepler, teme_to_ecef, ecef_to_geodetic,
    gmst_at_epoch, propagate_orbit
)

SAMPLE_ISS_TLE = TLEInput(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   26279.52445602  .00014285  00000+0  25833-3 0  9993",
    line2="2 25544  51.6415 120.4560 0005423  75.1234 285.0123 15.49875412589412"
)

SAMPLE_GEO_TLE = TLEInput(
    name="GOES-16",
    line1="1 41866U 16071A   26279.12345678 -.00000123  00000+0  00000+0 0  9991",
    line2="2 41866   0.0450  45.1234 0001234  12.3456 123.4567  1.00273791 32145"
)

class TestSGP4Engine(unittest.TestCase):
    def test_parse_tle_elements(self):
        elem = parse_tle(SAMPLE_ISS_TLE)
        self.assertEqual(elem["norad_id"], 25544)
        self.assertEqual(round(elem["inclination_deg"], 2), 51.64)
        self.assertTrue(90.0 < elem["period_minutes"] < 95.0)
        self.assertLess(elem["eccentricity"], 0.01)

    def test_solve_kepler_circular(self):
        E = solve_kepler(math.pi / 2.0, 0.0)
        self.assertAlmostEqual(E, math.pi / 2.0, places=5)

    def test_solve_kepler_eccentric(self):
        M = 1.0
        e = 0.5
        E = solve_kepler(M, e)
        calc_M = E - e * math.sin(E)
        self.assertAlmostEqual(calc_M, M, places=5)

    def test_ecef_to_geodetic_equator(self):
        lat, lon, alt = ecef_to_geodetic(6378.137, 0.0, 0.0)
        self.assertAlmostEqual(lat, 0.0, places=2)
        self.assertAlmostEqual(lon, 0.0, places=2)
        self.assertAlmostEqual(alt, 0.0, places=2)

    def test_ecef_to_geodetic_north_pole(self):
        lat, lon, alt = ecef_to_geodetic(0.0, 0.0, 6356.752)
        self.assertAlmostEqual(lat, 90.0, places=1)

    def test_gmst_continuity(self):
        dt1 = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
        g1 = gmst_at_epoch(dt1)
        g2 = gmst_at_epoch(dt2)
        diff = (g2 - g1) % (2 * math.pi)
        self.assertAlmostEqual(diff, math.pi, places=1)

    def test_propagate_iss_altitude(self):
        t = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
        state = propagate_orbit(SAMPLE_ISS_TLE, t)
        # ISS orbits between 380 and 460 km
        self.assertTrue(380.0 <= state.altitude_km <= 460.0)
        self.assertTrue(7.0 <= state.orbital_speed_kms <= 8.0)
        self.assertTrue(-55.0 <= state.latitude_deg <= 55.0)

    def test_propagate_geo_altitude(self):
        t = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)
        state = propagate_orbit(SAMPLE_GEO_TLE, t)
        # Geostationary altitude around ~35,786 km (near-zero ECEF relative velocity)
        self.assertTrue(35000.0 <= state.altitude_km <= 37000.0)
        self.assertLessEqual(state.orbital_speed_kms, 0.5)

if __name__ == "__main__":
    unittest.main()

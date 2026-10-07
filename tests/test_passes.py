import unittest
from app.models import TLEInput, GroundStation
from app.pass_predictor import geodetic_to_ecef, compute_aer, predict_passes

SAMPLE_ISS = TLEInput(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   26279.52445602  .00014285  00000+0  25833-3 0  9993",
    line2="2 25544  51.6415 120.4560 0005423  75.1234 285.0123 15.49875412589412"
)

LONDON_GS = GroundStation(
    name="London Ground Station",
    latitude_deg=51.5074,
    longitude_deg=-0.1278,
    altitude_m=30.0,
    min_elevation_deg=10.0
)

SVALBARD_GS = GroundStation(
    name="Svalbard Polar Station",
    latitude_deg=78.2297,
    longitude_deg=15.4077,
    altitude_m=450.0,
    min_elevation_deg=5.0
)

class TestPassPredictor(unittest.TestCase):
    def test_geodetic_to_ecef(self):
        x, y, z = geodetic_to_ecef(0.0, 0.0, 0.0)
        self.assertEqual(round(x, 1), 6378.1)
        self.assertEqual(round(y, 1), 0.0)
        self.assertEqual(round(z, 1), 0.0)

    def test_compute_aer_overhead(self):
        gs_x, gs_y, gs_z = geodetic_to_ecef(0.0, 0.0, 0.0)
        sat_ecef = [gs_x + 400.0, gs_y, gs_z]
        sat_v = [0.0, 7.5, 0.0]
        az, el, rng, r_rate = compute_aer(sat_ecef, sat_v, 0.0, 0.0, 0.0)
        self.assertLess(abs(el - 90.0), 1.0)
        self.assertEqual(round(rng, 1), 400.0)

    def test_predict_passes_structure(self):
        res = predict_passes(SAMPLE_ISS, LONDON_GS, window_hours=12, sample_step_sec=30)
        self.assertEqual(res.satellite_name, "ISS (ZARYA)")
        self.assertEqual(res.ground_station_name, "London Ground Station")
        self.assertIsInstance(res.passes, list)

    def test_pass_timing_consistency(self):
        res = predict_passes(SAMPLE_ISS, LONDON_GS, window_hours=24, sample_step_sec=15)
        for p in res.passes:
            self.assertLess(p.aos, p.tca)
            self.assertLess(p.tca, p.los)
            self.assertGreaterEqual(p.max_elevation_deg, 10.0)
            self.assertGreater(p.duration_seconds, 0)

    def test_pass_azimuth_ranges(self):
        res = predict_passes(SAMPLE_ISS, LONDON_GS, window_hours=24, sample_step_sec=15)
        for p in res.passes:
            self.assertTrue(0.0 <= p.azimuth_aos_deg <= 360.0)
            self.assertTrue(0.0 <= p.azimuth_los_deg <= 360.0)

    def test_pass_polar_coverage(self):
        res = predict_passes(SAMPLE_ISS, SVALBARD_GS, window_hours=12, sample_step_sec=30)
        self.assertIsInstance(res.passes, list)

if __name__ == "__main__":
    unittest.main()

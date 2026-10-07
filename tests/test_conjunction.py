import unittest
from app.models import TLEInput
from app.conjunction import compute_conjunction_assessment

PRIMARY_SAT = TLEInput(
    name="CHERUB-1",
    line1="1 99001U 26001A   26279.50000000  .00010000  00000+0  10000-3 0  9990",
    line2="2 99001  51.6000 100.0000 0001000  50.0000 300.0000 15.50000000    10"
)

DEBRIS_COLLISION = TLEInput(
    name="DEBRIS-CZ-4B",
    line1="1 99002U 26001B   26279.50000000  .00010000  00000+0  10000-3 0  9991",
    line2="2 99002  51.6000 100.0000 0001000  50.0000 300.0000 15.50000000    11"
)

DISTANT_SAT = TLEInput(
    name="POLAR-SAT-9",
    line1="1 99003U 26001C   26279.50000000  .00000000  00000+0  00000+0 0  9992",
    line2="2 99003  98.5000 250.0000 0001000  10.0000 190.0000 14.20000000    12"
)

class TestConjunctionCAM(unittest.TestCase):
    def test_conjunction_critical_detection(self):
        assessment = compute_conjunction_assessment(PRIMARY_SAT, DEBRIS_COLLISION, window_hours=2, time_step_sec=10)
        self.assertEqual(assessment.risk_level, "CRITICAL")
        self.assertLess(assessment.miss_distance_km, 1.0)
        self.assertGreater(assessment.collision_probability, 1e-4)
        self.assertIsNotNone(assessment.delta_v_vector_mps)

    def test_conjunction_distant_nominal(self):
        assessment = compute_conjunction_assessment(PRIMARY_SAT, DISTANT_SAT, window_hours=2, time_step_sec=60)
        self.assertIn(assessment.risk_level, ["NOMINAL", "WARNING"])
        self.assertGreater(assessment.miss_distance_km, 5.0)

    def test_conjunction_assessment_fields(self):
        assessment = compute_conjunction_assessment(PRIMARY_SAT, DISTANT_SAT, window_hours=1, time_step_sec=60)
        self.assertEqual(assessment.primary_name, "CHERUB-1")
        self.assertEqual(assessment.secondary_name, "POLAR-SAT-9")
        self.assertIsNotNone(assessment.tca)

    def test_conjunction_probability_bounds(self):
        assessment = compute_conjunction_assessment(PRIMARY_SAT, DEBRIS_COLLISION, window_hours=1, time_step_sec=10)
        self.assertTrue(0.0 <= assessment.collision_probability <= 1.0)

    def test_conjunction_delta_v_thrust(self):
        assessment = compute_conjunction_assessment(PRIMARY_SAT, DEBRIS_COLLISION, window_hours=1, time_step_sec=10)
        if assessment.risk_level == "CRITICAL":
            self.assertEqual(len(assessment.delta_v_vector_mps), 3)
            self.assertGreater(assessment.delta_v_vector_mps[0], 0.0)

    def test_conjunction_custom_threshold(self):
        assessment = compute_conjunction_assessment(PRIMARY_SAT, DISTANT_SAT, window_hours=1, threshold_km=1.0, time_step_sec=60)
        if assessment.miss_distance_km > 1.0:
            self.assertEqual(assessment.risk_level, "NOMINAL")

if __name__ == "__main__":
    unittest.main()

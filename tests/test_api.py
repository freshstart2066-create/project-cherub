import unittest
from app.main import app, validate_tle, propagate, list_ground_stations, create_telecommand
from app.models import TLEInput, PropagationRequest, TelecommandRequest

SAMPLE_ISS_TLE = TLEInput(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   26279.52445602  .00014285  00000+0  25833-3 0  9993",
    line2="2 25544  51.6415 120.4560 0005423  75.1234 285.0123 15.49875412589412"
)

class TestCherubAPI(unittest.TestCase):
    def test_tle_validation_function(self):
        res = validate_tle(SAMPLE_ISS_TLE)
        self.assertTrue(res["valid"])
        self.assertEqual(res["norad_id"], 25544)

    def test_propagation_function(self):
        req = PropagationRequest(
            tle=SAMPLE_ISS_TLE,
            duration_minutes=10,
            step_seconds=60
        )
        res = propagate(req)
        self.assertEqual(res.satellite_name, "ISS (ZARYA)")
        self.assertEqual(len(res.points), 11)

    def test_groundstations_function(self):
        gs_list = list_ground_stations()
        self.assertGreaterEqual(len(gs_list), 4)
        names = [g.name for g in gs_list]
        self.assertIn("London Gateway", names)

    def test_telecommand_function(self):
        cmd = TelecommandRequest(
            satellite_id="CHERUB-1",
            command_type="ORBIT_MANEUVER",
            parameters={"delta_v": 0.42}
        )
        pkt = create_telecommand(cmd)
        self.assertEqual(pkt.packet_type, "TELECOMMAND")
        self.assertTrue(pkt.checksum_valid)

if __name__ == "__main__":
    unittest.main()

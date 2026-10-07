import unittest
from app.models import TelecommandRequest
from app.c2_telecommand import frame_ccsds_telecommand, crc16_ccitt

class TestC2Telecommand(unittest.TestCase):
    def test_crc16_integrity(self):
        data = b"123456789"
        crc = crc16_ccitt(data)
        self.assertEqual(crc, 0x29B1)

    def test_frame_ccsds_orbit_maneuver(self):
        cmd = TelecommandRequest(
            satellite_id="CHERUB-1",
            command_type="ORBIT_MANEUVER",
            parameters={"delta_v_x": 0.42, "burn_duration_sec": 12.5}
        )
        pkt = frame_ccsds_telecommand(cmd, sequence_count=42)
        self.assertEqual(pkt.packet_type, "TELECOMMAND")
        self.assertEqual(pkt.apid, 0x0120)
        self.assertEqual(pkt.sequence_count, 42)
        self.assertTrue(pkt.checksum_valid)
        self.assertGreater(len(pkt.data_field_hex), 20)

    def test_frame_ccsds_sensor_swath(self):
        cmd = TelecommandRequest(
            satellite_id="CHERUB-1",
            command_type="SENSOR_SWATH",
            parameters={"mode": "HYPERSPECTRAL", "fov_deg": 45.0}
        )
        pkt = frame_ccsds_telecommand(cmd, sequence_count=1)
        self.assertEqual(pkt.apid, 0x0130)
        self.assertEqual(pkt.status, "QUEUED_FOR_UPLINK")

    def test_frame_ccsds_safe_mode(self):
        cmd = TelecommandRequest(
            satellite_id="CHERUB-1",
            command_type="SAFE_MODE",
            parameters={"reason": "POWER_ANOMALY"}
        )
        pkt = frame_ccsds_telecommand(cmd)
        self.assertEqual(pkt.apid, 0x0100)

    def test_frame_ccsds_attitude_slew(self):
        cmd = TelecommandRequest(
            satellite_id="CHERUB-1",
            command_type="ATTITUDE_SLEW",
            parameters={"roll": 0.0, "pitch": 15.0, "yaw": -5.0}
        )
        pkt = frame_ccsds_telecommand(cmd)
        self.assertEqual(pkt.apid, 0x0140)

    def test_frame_ccsds_hex_payload_parseable(self):
        cmd = TelecommandRequest(
            satellite_id="CHERUB-1",
            command_type="ORBIT_MANEUVER",
            parameters={"thrust_n": 50.0}
        )
        pkt = frame_ccsds_telecommand(cmd)
        raw_bytes = bytes.fromhex(pkt.data_field_hex)
        self.assertGreaterEqual(len(raw_bytes), 8)

if __name__ == "__main__":
    unittest.main()

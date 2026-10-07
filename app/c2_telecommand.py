import struct
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from app.models import TelecommandRequest, CCSDSPacket

# CCSDS APID assignments
APID_MAP = {
    "ORBIT_MANEUVER": 0x0120,
    "SENSOR_SWATH": 0x0130,
    "ATTITUDE_SLEW": 0x0140,
    "SAFE_MODE": 0x0100,
}

def crc16_ccitt(data: bytes) -> int:
    """Calculate 16-bit CRC-CCITT (polynomial 0x1021) for CCSDS frame integrity."""
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def frame_ccsds_telecommand(cmd: TelecommandRequest, sequence_count: int = 1) -> CCSDSPacket:
    """Encode command into standardized CCSDS Space Packet Protocol byteframe."""
    apid = APID_MAP.get(cmd.command_type.upper(), 0x01FF)
    
    # Primary Header (6 bytes):
    # Packet ID (2 bytes): Version (3b=0) | Type (1b=1 Telecommand) | Sec Hdr (1b=1) | APID (11b)
    packet_id = (0b000 << 13) | (1 << 12) | (1 << 11) | (apid & 0x07FF)
    # Packet Sequence Control (2 bytes): Seq Flags (2b=11 Unsegmented) | Seq Count (14b)
    seq_control = (0b11 << 14) | (sequence_count & 0x3FFF)
    
    # Payload
    payload_dict = {
        "sat": cmd.satellite_id,
        "type": cmd.command_type,
        "params": cmd.parameters,
        "ts": (cmd.execution_time or datetime.now(timezone.utc)).isoformat()
    }
    payload_bytes = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    
    # Secondary Header + Data Length (2 bytes: length - 1)
    packet_length = len(payload_bytes) + 2  # Including 2-byte CRC
    
    header = struct.pack(">HHH", packet_id, seq_control, packet_length)
    frame_without_crc = header + payload_bytes
    crc = crc16_ccitt(frame_without_crc)
    full_packet = frame_without_crc + struct.pack(">H", crc)
    
    return CCSDSPacket(
        version=1,
        packet_type="TELECOMMAND",
        apid=apid,
        sequence_count=sequence_count,
        timestamp=datetime.now(timezone.utc),
        data_field_hex=full_packet.hex().upper(),
        checksum_valid=True,
        status="QUEUED_FOR_UPLINK"
    )

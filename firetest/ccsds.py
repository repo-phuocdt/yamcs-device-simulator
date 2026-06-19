"""CCSDS codec for the firetest device (verified against the Yamcs MDB + CsvRecorderService).

TM packet — 20 bytes, big-endian:
  [0-1]   apid word    : version(3) | type(1) | sec-hdr-flag(1)=1 | apid(11)
  [2-3]   seq word     : seqFlags(2)=3 | seqCount(14)
  [4-5]   packet length: 13 (0x000D)
  [6-9]   coarse time  : epoch seconds (uint32)
  [10-11] fine time    : milliseconds remainder (uint16)
  [12-15] packet-id    : int32  (1 = TestFlag; 1..10 = sensor data)
  [16-19] payload      : float32 value (data) OR byte 16 = flag (TestFlag)

TC packet (received on yamcs-tc-packets) = [8-byte START_ENGINE command][4-byte seqCount].
start_engine (1=On, 0=Off) is byte 7; apid 400, packet-id 1.
No CRC trailer — the Yamcs preprocessor's checksum check is disabled.
"""
import struct
import time

DATA_APID = 101
TESTFLAG_APID = 401
TESTFLAG_PACKET_ID = 1
TC_APID = 400
TC_PACKET_ID = 1

_TM = struct.Struct(">HHHIHi")  # header through packet-id (16 bytes); payload appended after
_SEC_HDR_FLAG = 1
_PACKET_LENGTH_FIELD = (6 + 8) - 1  # secondary(6) + payload(8) - 1 = 13

_seq = 0


def _header(apid: int, packet_id: int, now_ms: int) -> bytearray:
    global _seq
    apid_word = (0 << 13) | (0 << 12) | (_SEC_HDR_FLAG << 11) | (apid & 0x7FF)
    seq_word = (3 << 14) | (_seq & 0x3FFF)
    _seq = (_seq + 1) & 0x3FFF
    coarse = (now_ms // 1000) & 0xFFFFFFFF
    fine = now_ms % 1000
    return bytearray(_TM.pack(apid_word, seq_word, _PACKET_LENGTH_FIELD, coarse, fine, packet_id))


def build_data_packet(packet_id, value, apid=DATA_APID, now_ms=None):
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    buf = _header(apid, packet_id, now_ms)
    buf += struct.pack(">f", value)
    return bytes(buf)


def build_testflag_packet(flag, now_ms=None):
    """flag=1 arms a sequence (CsvRecorderService records); flag=0 finishes it."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    buf = _header(TESTFLAG_APID, TESTFLAG_PACKET_ID, now_ms)
    buf += bytes([1 if flag else 0, 0, 0, 0])  # byte 16 = flag, pad to 20 bytes
    return bytes(buf)


def decode_tc(buffer: bytes):
    """Decode a START_ENGINE TC. Returns dict {on_off, start_engine, apid, packet_id, valid}."""
    raw = bytes(buffer)
    if len(raw) < 8:
        return {"on_off": None, "start_engine": None, "apid": None, "packet_id": None, "valid": False}
    apid = struct.unpack(">H", raw[0:2])[0] & 0x7FF
    packet_id = struct.unpack(">i", raw[3:7])[0]
    start_engine = raw[7]
    valid = apid == TC_APID and packet_id == TC_PACKET_ID and len(raw) >= 12
    return {
        "on_off": start_engine == 1,
        "start_engine": start_engine,
        "apid": apid,
        "packet_id": packet_id,
        "valid": valid,
    }

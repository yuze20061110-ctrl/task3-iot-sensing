"""State shared between the 500 Hz control loop (core0) and the network
thread (core1).  Plain dict: writes are atomic enough for scalars and the
network side only ever reads a snapshot."""
STATE = {
    "gz": 0.0, "gy": 0.0, "gz_peak": 0.0,
    "temp": 0.0, "vsys": 0.0, "rssi": 0,
    "shots": 0, "shots_window": 0,
    "present": 0, "session_s": 0, "sessions": 0,
    "uploaded": 0, "last_up": -1, "net": "off",
    "cfg": {"gear": 1, "dz": 4, "lp": 35},
    "samples": [],
}

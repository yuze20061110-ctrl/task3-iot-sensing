"""Data layer for the desktop application.

Three interchangeable sources behind one interface, so the UI never knows (or
cares) where a reading came from:

  MockSource        synthetic, always available, used for development and demos
  ThingSpeakSource  the real cloud channel (needs a channel id + read key)
  SerialSource      the USB CDC link, ~1 Hz, lowest latency (G HUB feel)

Every source exposes .poll() -> dict and keeps .history (last 240 readings).
"""
import json, math, os, time, random

try:
    import urllib.request as _urlreq
except Exception:
    _urlreq = None

FIELDS = 8
HISTORY = 240


def find_pico_port():
    """Return the serial device of a Raspberry Pi Pico, or None.

    The board enumerates with vendor id 0x2E8A; the console/REPL interface and the
    data interface share that id, so the first match is used.
    """
    try:
        from serial.tools import list_ports
    except Exception:
        return None
    for p in list_ports.comports():
        try:
            if p.vid == 0x2E8A:
                return p.device
        except Exception:
            continue
    return None


class Source(object):
    name = "base"

    def __init__(self):
        self.latest = {}
        self.history = []
        self.online = False
        self.note = ""

    def _push(self, d):
        self.latest = d
        self.history.append(d)
        while len(self.history) > HISTORY:
            self.history.pop(0)
        return d

    def poll(self):
        return self.latest

    def send(self, text):
        """Push a command to the device.  Returns a short human-readable status."""
        return "unsupported"

    def close(self):
        pass


class MockSource(Source):
    name = "mock"

    def __init__(self):
        super().__init__()
        self.t0 = time.time()
        self.shots = 0
        self.sess_start = time.time()
        self.online = True
        self.note = "synthetic data"

    def send(self, text):
        self.note = "mock accepted: " + text
        return "mock accepted"

    def poll(self):
        t = time.time() - self.t0
        gz = -0.6 + 26 * math.sin(t * 0.9) + random.uniform(-2.5, 2.5)
        gy = 1.4 + 11 * math.sin(t * 1.7 + 1.0) + random.uniform(-1.8, 1.8)
        if random.random() < 0.045:
            self.shots += 1
        wave = [max(0, min(255, int(abs(gz) + random.uniform(-3, 3))))]
        prev = self.history[-1]["wave"][-15:] if self.history else []
        wave = (prev + wave)[-15:]
        return self._push({
            "gz": gz, "gy": gy, "temp": 32.5 + 0.3 * math.sin(t * 0.05),
            "shots": self.shots, "present": 1,
            "session_s": int(time.time() - self.sess_start),
            "vsys": 4.92 + 0.02 * math.sin(t), "rssi": -62 + int(4 * math.sin(t * 0.3)),
            "uploaded": int(t // 15), "wave": wave, "net": "mock",
        })


class ThingSpeakSource(Source):
    name = "thingspeak"

    def __init__(self, channel, read_key, results=60, timeout=8,
                 cmd_channel=None, cmd_write=None):
        super().__init__()
        self.channel = str(channel)
        self.read_key = read_key
        self.cmd_channel = cmd_channel
        self.cmd_write = cmd_write
        self.results = results
        self.timeout = timeout
        self.note = "channel %s" % self.channel

    def send(self, text):
        if not self.cmd_channel or not self.cmd_write:
            return "no command channel configured"
        parts = text.replace("#CFG", "").split()
        try:
            gear, dz, lp = int(parts[0]), int(parts[1]), int(parts[2])
        except Exception:
            return "bad command: %s" % (text,)
        url = ("https://api.thingspeak.com/update?api_key=%s&field1=%d&field2=%d&field3=%d"
               % (self.cmd_write, gear, dz, lp))
        try:
            with _urlreq.urlopen(url, timeout=self.timeout) as r:
                r.read()
            self.note = "command channel updated"
            return "cloud accepted"
        except Exception as e:
            return "cloud write failed: %s" % (e,)

    def poll(self):
        if _urlreq is None:
            self.note = "urllib unavailable"
            return self.latest
        url = ("https://api.thingspeak.com/channels/%s/feeds.json?api_key=%s&results=%d"
               % (self.channel, self.read_key, self.results))
        try:
            with _urlreq.urlopen(url, timeout=self.timeout) as r:
                d = json.loads(r.read().decode())
        except Exception as e:
            self.online = False
            self.note = "read failed: %s" % (e,)
            return self.latest

        feeds = d.get("feeds") or []
        if not feeds:
            self.online = False
            self.note = "channel empty"
            return self.latest

        self.history = []
        for f in feeds:
            self._push(self._row(f))
        self.online = True
        self.note = "channel %s · %d rows" % (self.channel, len(feeds))
        self.latest["rows"] = len(feeds)
        return self.latest

    @staticmethod
    def _num(f, k, dflt=0.0):
        v = f.get("field%d" % k)
        try:
            return float(v)
        except (TypeError, ValueError):
            return dflt

    @classmethod
    def _row(cls, f):
        wave = []
        packed = f.get("field8") or ""
        if packed:
            try:
                import base64
                s = packed.replace("-", "+").replace("_", "/")
                s += "=" * (-len(s) % 4)
                wave = list(base64.b64decode(s))
            except Exception:
                wave = []
        return {
            "gz": cls._num(f, 1), "gy": cls._num(f, 2), "temp": cls._num(f, 3),
            "shots": int(cls._num(f, 4)), "present": int(cls._num(f, 5)),
            "session_s": int(cls._num(f, 6)), "vsys": cls._num(f, 7),
            "rssi": 0, "uploaded": 0, "wave": wave, "net": "cloud",
            "at": f.get("created_at", ""),
        }


class SerialSource(Source):
    """Reads '@gz|gy|temp|shots|present|session|vsys' lines from the Pico."""
    name = "serial"

    def __init__(self, port=None, baud=115200):
        super().__init__()
        self.baud = baud
        self.port = port or find_pico_port()
        self.ser = None
        self._buf = ""
        self._retry_at = 0.0
        self._ack_at = 0.0
        self.note = "no Pico found"
        self._open()

    def _open(self):
        if not self.port:
            self.port = find_pico_port()
        if not self.port:
            self.note = "no Pico found"
            return False
        try:
            import serial
            self.ser = serial.Serial(self.port, self.baud, timeout=0.2)
            self.ser.setDTR(False)
            self.ser.setRTS(False)
            self.online = True
            self.note = "connected " + str(self.port)
            return True
        except Exception as e:
            self.ser = None
            self.online = False
            self.note = "open failed: %s" % (e,)
            return False

    def send(self, text):
        if self.ser is None:
            return "port not open"
        try:
            self.ser.write((text + "\n").encode())
            return "sent over " + str(self.ser.port)
        except Exception as e:
            return "write failed: %s" % (e,)

    def poll(self):
        import time as _t
        if self.ser is not None and _t.time() - getattr(self, "_ack_at", 0.0) > 6.0:
            self.note = "streaming %s" % self.ser.port
        if self.ser is None:
            now = _t.time()
            if now >= self._retry_at:
                self._retry_at = now + 2.0
                self._open()
            if self.ser is None:
                return self.latest
        try:
            n = self.ser.in_waiting
            raw = self.ser.read(n) if n else b""
        except Exception as e:
            self.note = "read failed: %s" % (e,)
            return self.latest
        if not raw:
            return self.latest
        text = getattr(self, "_buf", "") + raw.decode("utf-8", "replace")
        *lines, self._buf = text.split("\n")
        for ln in lines:
            ln = ln.strip()
            if ln.startswith("#ACK"):
                import time as _t
                self.note = "device: " + ln[5:].strip()
                self._ack_at = _t.time()
                continue
            if not ln.startswith("@"):
                continue
            try:
                p = ln[1:].split("|")
                d = {
                    "gz": float(p[0]), "gy": float(p[1]), "temp": float(p[2]),
                    "shots": int(float(p[3])), "present": int(float(p[4])),
                    "session_s": int(float(p[5])), "vsys": float(p[6]),
                    "rssi": 0, "uploaded": 0, "wave": [], "net": "serial",
                }
                prev = self.latest.get("wave") or []
                d["wave"] = (prev + [max(0, min(255, int(abs(d["gz"]))))])[-15:]
                self._push(d)
                self.online = True
            except Exception:
                continue
        return self.latest

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass


class SessionLog(object):
    """Turns the presence flag into a log of usage periods.

    A period opens when the infrared sensor first sees the operator and closes
    when it loses them, so every row is one real engagement.
    """

    def __init__(self, path=None):
        self.path = path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'sessions.json')
        self.rows = []
        self.open_row = None
        self._load()

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self.rows = json.load(f).get('rows', [])[-200:]
        except Exception:
            self.rows = []

    def _save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({'rows': self.rows[-200:]}, f)
        except Exception:
            pass

    def update(self, d):
        present = int(d.get('present') or 0)
        shots = int(d.get('shots') or 0)
        now = time.time()
        if present and self.open_row is None:
            self.open_row = {'start': now, 'shots': shots, 'dur': 0, 'live': 1}
        elif present and self.open_row is not None:
            self.open_row['shots'] = shots
            secs = int(d.get('session_s') or 0)
            if secs:
                self.open_row['dur'] = secs
        elif not present and self.open_row is not None:
            row = self.open_row
            row.pop('live', None)
            row['dur'] = row.get('dur') or int(now - row['start'])
            self.rows.append(row)
            self.open_row = None
            self._save()
        return self.rows

    def live(self):
        rows = list(self.rows)
        if self.open_row is not None:
            rows = rows + [dict(self.open_row)]
        return rows

def make_source(kind="mock", **kw):
    kind = (kind or "mock").lower()
    if kind.startswith("thingspeak") or kind == "cloud":
        return ThingSpeakSource(kw.get("channel", ""), kw.get("read_key", ""),
                                cmd_channel=kw.get("cmd_channel"),
                                cmd_write=kw.get("cmd_write"))
    if kind.startswith("serial"):
        return SerialSource(kw.get("port", "COM13"))
    return MockSource()
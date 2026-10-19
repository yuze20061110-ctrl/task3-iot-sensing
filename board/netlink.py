"""WiFi + ThingSpeak bridge.  Runs on core1 so the 500 Hz HID loop on core0 is
never blocked.  Does nothing at all unless ts_cfg has a channel and write key.

Uplink  (every UPLOAD_S seconds) -> 8 fields
  field1 gyro gz mean (dps)      field5 PIR operator present (0/1)
  field2 gyro gy mean (dps)      field6 session length (s)
  field3 MPU temperature (C)     field7 supply voltage (V)
  field4 shots in window         field8 15x 1 Hz |gz| samples, url-safe base64

Downlink (every CMD_POLL_S) <- command channel
  field1 sensitivity gear (1..3)  field2 deadzone x10   field3 low-pass Hz
"""
import _thread, time, binascii

try:
    import urequests as _http
except Exception:
    try:
        import requests as _http
    except Exception:
        _http = None

import shared

LOG = "/net.log"
_started = False


def _log(m):
    try:
        f = open(LOG, "a")
        f.write("%d %s\n" % (time.ticks_ms(), m))
        f.close()
    except Exception:
        pass


def _b64u(bs):
    s = binascii.b2a_base64(bytes(bs)).decode().strip()
    return s.replace("+", "-").replace("/", "_").replace("=", "")


def _get(url, timeout=12):
    if _http is None:
        return None
    try:
        r = _http.get(url, timeout=timeout)
    except TypeError:
        r = _http.get(url)
    except Exception as e:
        _log("GET fail %r" % (e,))
        return None
    try:
        txt = r.text
    except Exception:
        txt = ""
    try:
        r.close()
    except Exception:
        pass
    return txt


def _connect(cfg):
    try:
        import network
    except Exception as e:
        _log("no network module %r" % (e,))
        return None
    try:
        import ts_cfg
    except Exception:
        ts_cfg = cfg
    ssid = getattr(ts_cfg, "WIFI_SSID", "") or cfg.get("ssid", "")
    pw = getattr(ts_cfg, "WIFI_PASS", "") or cfg.get("pass", "")
    if not ssid:
        _log("no wifi credentials")
        return None
    w = network.WLAN(network.STA_IF)
    w.active(True)
    if not w.isconnected():
        w.connect(ssid, pw)
        t0 = time.ticks_ms()
        while not w.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 25000:
                _log("wifi timeout")
                return None
            time.sleep_ms(250)
    try:
        shared.STATE["rssi"] = w.status("rssi")
    except Exception:
        pass
    _log("wifi up")
    return w


def _upload(cfg, st):
    fields = []
    samples = st.get("samples") or []
    vals = [
        "%.2f" % st.get("gz", 0.0),
        "%.2f" % st.get("gy", 0.0),
        "%.2f" % st.get("temp", 0.0),
        str(int(st.get("shots_window", 0))),
        str(int(st.get("present", 0))),
        str(int(st.get("session_s", 0))),
        "%.2f" % st.get("vsys", 0.0),
        _b64u(samples[-15:]) if samples else "",
    ]
    for i, v in enumerate(vals):
        fields.append("field%d=%s" % (i + 1, v))
    url = ("http://api.thingspeak.com/update?api_key=%s&%s"
           % (cfg["write_key"], "&".join(fields)))
    r = _get(url, 15)
    if r is not None:
        st["uploaded"] = st.get("uploaded", 0) + 1
        st["last_up"] = time.ticks_ms()
    else:
        _log("upload failed")


def _poll_cmd(cfg, st):
    if not cfg.get("cmd_id") or not cfg.get("cmd_read"):
        return
    url = ("http://api.thingspeak.com/channels/%s/feeds/last.json?api_key=%s"
           % (cfg["cmd_id"], cfg["cmd_read"]))
    txt = _get(url, 12)
    if not txt:
        return
    try:
        import json
        d = json.loads(txt)
        c = st["cfg"]
        f1 = d.get("field1")
        f2 = d.get("field2")
        f3 = d.get("field3")
        if f1:
            c["gear"] = max(1, min(3, int(float(f1))))
        if f2:
            c["dz"] = max(0, min(20, int(float(f2))))
        if f3:
            c["lp"] = max(10, min(60, int(float(f3))))
        _log("cmd %s" % (c,))
    except Exception as e:
        _log("cmd parse %r" % (e,))


def _run(cfg):
    w = _connect(cfg)
    if w is None:
        shared.STATE["net"] = "no-wifi"
        return
    st = shared.STATE
    st["net"] = "up"
    last_up = 0
    last_cmd = 0
    while True:
        now = time.ticks_ms()
        if time.ticks_diff(now, last_up) >= cfg["upload_s"] * 1000:
            st["samples"] = []
            _upload(cfg, st)
            last_up = now
        if time.ticks_diff(now, last_cmd) >= cfg["cmd_poll_s"] * 1000:
            _poll_cmd(cfg, st)
            last_cmd = now
        try:
            st["rssi"] = w.status("rssi")
        except Exception:
            pass
        time.sleep_ms(500)


def start():
    """Returns 'disabled' unless a channel + write key are configured."""
    global _started
    if _started:
        return "already"
    try:
        import ts_cfg
    except Exception as e:
        _log("no ts_cfg %r" % (e,))
        return "no-config"
    if not getattr(ts_cfg, "TS_CH_ID", "") or not getattr(ts_cfg, "TS_WRITE_KEY", ""):
        shared.STATE["net"] = "off"
        return "disabled"
    cfg = {
        "ch": ts_cfg.TS_CH_ID,
        "write_key": ts_cfg.TS_WRITE_KEY,
        "read_key": getattr(ts_cfg, "TS_READ_KEY", ""),
        "cmd_id": getattr(ts_cfg, "TS_CMD_ID", ""),
        "cmd_read": getattr(ts_cfg, "TS_CMD_READ_KEY", ""),
        "upload_s": getattr(ts_cfg, "UPLOAD_S", 15),
        "cmd_poll_s": getattr(ts_cfg, "CMD_POLL_S", 30),
    }
    _started = True
    _thread.start_new_thread(_run, (cfg,))
    return "started"

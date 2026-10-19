# ThingSpeak / WiFi configuration template.
# Copy this file to ts_cfg.py and fill in your own values.
# Leave TS_CH_ID or TS_WRITE_KEY empty and the network layer stays completely
# off: the mouse keeps working and nothing is uploaded.
WIFI_SSID = ""
WIFI_PASS = ""

# telemetry channel (device writes, desktop app reads)
TS_CH_ID     = ""
TS_WRITE_KEY = ""   # device write key
TS_READ_KEY  = ""   # desktop read key

# command channel (desktop app writes, device reads)
TS_CMD_ID         = ""
TS_CMD_WRITE_KEY  = ""
TS_CMD_READ_KEY   = ""

SERIAL_TELEMETRY = True   # emit @gz|gy|temp|shots|present|session|vsys once per publish

UPLOAD_S = 15            # ThingSpeak free tier: one update per 15 s
CMD_POLL_S = 30

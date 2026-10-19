# Pico Gun Mouse - boot.py
# RULE #1: silence the active-low buzzer BEFORE anything else. A floating GP15
# makes it scream; this bit me once already.
from machine import Pin

try:
    Pin(15, Pin.OUT, value=1)
except Exception:
    pass

# RULE #2: never leave the unusable pins floating. The motherboard wires the
# onboard RGB (a WS2812 chain) and LED7/LED8 to some of these. A floating
# WS2812 data line is famous for randomly latching noise and flashing white.
# Parking them as inputs with a pull-up makes the state deterministic and also
# cannot damage anything (a weak pull never contends with an external driver).
#
# Pins the firmware actually uses and must NOT touch here:
#   0, 1   = I2C0 (MPU6500 @0x68 + SSD1306 @0x3C)
#   16 = HC-SR501 PIR presence sensor
#   12,13,14 = LEFT / DOWN / UP buttons
#   15     = buzzer (driven high above)
for _n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 20, 21, 22, 26, 27, 28):
    try:
        Pin(_n, Pin.IN, Pin.PULL_UP)
    except Exception:
        pass

# RULE #3: do NOT touch usb.device here. Installing the runtime USB device from
# boot.py hung the CDC on this firmware (COM13 enumerated but never answered
# SET_LINE_CODING, and the HID interface never appeared at all). The install
# happens at runtime from main.py, which is the path that was actually tested.
import time

held = 0
try:
    _p = Pin(14, Pin.IN, Pin.PULL_UP)
    time.sleep_ms(30)
    if _p.value() == 0:
        held = 1
except Exception:
    pass

try:
    _f = open('/safety.flag', 'w')
    _f.write(str(held))
    _f.close()
except Exception:
    pass
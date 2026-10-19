# Task 3 — Internet of Things Sensing System

Coursework for 6E5Z0025 Embedded Systems. A pistol-style inertial mouse that
reports to a cloud channel.

A Raspberry Pi Pico 2 W reads a six-axis IMU at 500 Hz, turns angular rate into
relative pointer motion, and presents itself to the host as a USB HID mouse so no
driver is needed. A passive infrared sensor detects the operator, an OLED reports
state locally, and the same measurements are published over WiFi to ThingSpeak and
rendered by a PyQt5 desktop application.

## Firmware architecture

The design decision that everything else follows from is the core split.

- **Core 0** runs the 500 Hz control loop and owns the USB HID device. Nothing here
  ever blocks: the mouse must not stutter because a network request is in flight.
- **Core 1** runs the network bridge as a single thread. Exactly one thread may use
  core 1 on the RP2350, so all background work — uploads, command polling, the
  serial link — is funnelled through it.
- The two cores exchange a plain dictionary (`shared.py`). The loop writes
  measurements into it and the bridge reads them out; neither waits on the other.

A hard gate rejects any capture whose standard deviation on any axis says the board
was moving, so a button press cannot move the pointer. A soft dead zone subtracts a
0.4 dps threshold, the gyro bias is estimated over a two-second still period, and a
first-order low-pass filter at 35 Hz removes quantisation noise.

## Desktop application

The PyQt5 client has five pages: the device card, the session log, the cloud
channel, the stored sensitivity profiles and a device detail page. Three
interchangeable data sources implement one interface — a synthetic source for
development, a ThingSpeak source that polls the channel over HTTPS, and a serial
source that reads the USB link at about one hertz. The pages receive a dictionary
and render it, so switching sources is a single constructor argument.

## Files

**Firmware (`board/`)**

| File | Purpose |
|---|---|
| `main.py` | entry point and safety guards |
| `boot.py` | pin parking and safety-flag read |
| `gunmouse.py` | 500 Hz control loop, calibration, macros |
| `hidmouse.py` | USB HID mouse driver |
| `netlink.py` | core-1 ThingSpeak bridge |
| `cmdlink.py` | serial command channel |
| `macros.py` | record and replay |
| `shared.py` | cross-core state dictionary |
| `ts_cfg.example.py` | configuration template |

**Desktop (`app/`)**

| File | Purpose |
|---|---|
| `app.py` | PyQt5 shell and the five pages |
| `ui.py` | widgets, icons and design tokens |
| `data.py` | three interchangeable data sources |
| `tokens.py` | measured design values |

## Running it

Firmware: copy `board/` to the Pico, then copy `ts_cfg.example.py` to `ts_cfg.py`
and fill in your own WiFi and ThingSpeak credentials.

```
python app/app.py
```

`ts_cfg.py` is deliberately excluded from this repository because it holds
credentials; only the template is published.

import time, struct, sys
import netlink
from machine import Pin, I2C
import hidmouse
import shared
import macros
import cmdlink

MPU = 0x68
FS = 16.4
RATE = 500
DT = 1.0 / RATE
DZ = 0.4
FC = 35.0
LPF_A = (2 * 3.14159265 * FC * DT) / (2 * 3.14159265 * FC * DT + 1.0)
GEARS = (9.0, 18.0, 36.0)
SETTLE_MS = 3000
CAL_MS = 2000
TAIL_DZ = 0.15
CLICK_MAX_MS = 400
HOLD_MS = 1500

UP = 14
DOWN = 13
LEFT = 12
BUZ = 15
PIR = 16
PRESENCE_HOLD_MS = 30000

RUNLOG = '/run.log'
FAULTLOG = '/fault.log'

STATS = {}
_buz = None


def _rl(m):
    try:
        f = open(RUNLOG, 'a')
        f.write(m + '\n')
        f.close()
    except Exception:
        pass


def _buz_off():
    global _buz
    try:
        if _buz is None:
            _buz = Pin(BUZ, Pin.OUT, value=1)
        else:
            _buz.value(1)
    except Exception:
        pass


def _wreg(i2c, r, v):
    i2c.writeto_mem(MPU, r, bytes([v]))


def mpu_init(i2c):
    _wreg(i2c, 0x6B, 0x00)
    time.sleep_ms(20)
    _wreg(i2c, 0x19, 0x01)
    _wreg(i2c, 0x1A, 0x03)
    _wreg(i2c, 0x1B, 0x18)
    _wreg(i2c, 0x1C, 0x00)
    time.sleep_ms(60)
    return i2c.readfrom_mem(MPU, 0x75, 1)[0]


def _read(i2c):
    d = i2c.readfrom_mem(MPU, 0x3B, 14)
    g = struct.unpack('>3h', d[8:14])
    t = struct.unpack('>h', d[6:8])[0]
    return g[0], g[1], g[2], t


class OLED:
    def __init__(self, i2c):
        self.ok = False
        self.o = None
        self.last = None
        try:
            import ssd1306
            self.o = ssd1306.SSD1306_I2C(128, 64, i2c)
            self.o.fill(0)
            self.o.show()
            self.ok = True
        except Exception as e:
            _rl('OLED init failed %r' % (e,))

    def render(self, gear, state, extra=''):
        if not self.ok:
            return False
        key = (gear, state, extra)
        if key == self.last:
            return False
        try:
            o = self.o
            o.fill(0)
            o.text('PICO GUN MOUSE', 0, 0)
            o.text('SENS %d/%d  %d c/deg' % (gear + 1, len(GEARS), int(GEARS[gear])), 0, 16)
            o.text(state, 0, 32)
            if extra:
                o.text(extra, 0, 48)
            o.show()
            self.last = key
        except Exception as e:
            self.ok = False
            _rl('OLED render failed %r' % (e,))
        return True


def beep(n=1, on=60, off=120):
    _buz_off()
    b = _buz
    for _ in range(n):
        b.value(0)
        time.sleep_ms(on)
        b.value(1)
        time.sleep_ms(off)


def calibrate(i2c, ms=CAL_MS):
    n = int(RATE * ms / 1000)
    sx = sy = sz = 0
    sxx = syy = 0
    t_next = time.ticks_ms()
    for _ in range(n):
        gx, gy, gz, _t = _read(i2c)
        sx += gx
        sy += gy
        sz += gz
        sxx += gx * gx
        syy += gy * gy
        t_next = time.ticks_add(t_next, 2)
        dt = time.ticks_diff(t_next, time.ticks_ms())
        if dt > 0:
            time.sleep_ms(dt)
    mx = sx / n
    my = sy / n
    sdx = (sxx / n - mx * mx) ** 0.5
    sdy = (syy / n - my * my) ** 0.5
    return (mx / FS, my / FS, sz / n / FS, sdx / FS, sdy / FS)


_LED = None
_LED_MS = 0


def _led_init():
    """Optional status LED on ts_cfg.PIN_LED.  None disables it."""
    global _LED
    if _LED is not None:
        return _LED
    try:
        import ts_cfg
        n = getattr(ts_cfg, 'PIN_LED', None)
        _LED = Pin(int(n), Pin.OUT, value=0) if n is not None else False
    except Exception:
        _LED = False
    return _LED


def _led_tick():
    """solid = uplink up, slow blink = no wifi, fast blink = not configured."""
    global _LED_MS
    if not _led_init():
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, _LED_MS) < 20:
        return
    _LED_MS = now
    net = shared.STATE.get('net')
    phase = (now // 60) % 16
    if net == 'up':
        on = 1
    elif net == 'no-wifi':
        on = 1 if phase < 3 else 0
    else:
        on = 1 if phase < 1 else 0
    try:
        _LED.value(on)
    except Exception:
        pass

def run():
    _buz_off()
    try:
        _run_inner()
    except KeyboardInterrupt:
        _rl('KEYBOARD INTERRUPT')
        raise
    except Exception as e:
        _rl('FAULT %r' % (e,))
        try:
            f = open(FAULTLOG, 'w')
            sys.print_exception(e, f)
            f.close()
        except Exception:
            pass
        raise
    finally:
        _buz_off()
        g = hidmouse.get()
        if g is not None:
            try:
                g.release_all()
                g.kick()
            except Exception:
                pass


def _run_inner():
    global STATS
    try:
        import os
        os.remove(RUNLOG)
    except Exception:
        pass
    try:
        import os
        os.remove(FAULTLOG)
    except Exception:
        pass
    _rl('=== boot ===')

    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
    who = mpu_init(i2c)
    _rl('mpu who=0x%02X regs=%s' % (who, str(regs(i2c))))
    oled = OLED(i2c)
    _rl('oled ok=%s' % oled.ok)
    oled.render(0, 'BOOTING', 'imu 0x%02X' % who)

    gm = hidmouse.install(interval_ms=1)
    _rl('hid installed')

    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < SETTLE_MS:
        left = 3 - time.ticks_diff(time.ticks_ms(), t0) // 1000
        if left < 0:
            left = 0
        oled.render(0, 'SETTLING', 'host ready in %ds' % left)
        time.sleep_ms(200)
    _rl('settled is_open=%s' % gm.is_open())

    # Calibration must be REJECTED if the board is moving: a contaminated bias
    # of ~1.5 dps blows straight through the 0.4 dps deadzone and the pointer
    # drifts on its own forever. Healthy sd is ~0.06-0.07 dps at +-2000 dps.
    CAL_SD_MAX = 0.30
    best = None
    for attempt in range(6):
        oled.last = None
        oled.render(0, 'CALIBRATING', 'hold still %d' % (attempt + 1))
        time.sleep_ms(120)
        bx, by, bz, cx, cy = calibrate(i2c)
        _rl('cal#%d bias=(%.3f,%.3f,%.3f) sd=(%.3f,%.3f)' % (attempt + 1, bx, by, bz, cx, cy))
        if best is None or (cx + cy) < (best[3] + best[4]):
            best = (bx, by, bz, cx, cy)
        if cx < CAL_SD_MAX and cy < CAL_SD_MAX:
            break
        oled.last = None
        oled.render(0, 'MOVING!', 'hold still, retry')
        beep(2, on=40, off=90)
    bias_x, bias_y, bias_z, sdx, sdy = best
    _rl('cal ACCEPTED bias=(%.3f,%.3f,%.3f) sd=(%.3f,%.3f)' % (bias_x, bias_y, bias_z, sdx, sdy))
    oled.last = None

    up = Pin(UP, Pin.IN, Pin.PULL_UP)
    dn = Pin(DOWN, Pin.IN, Pin.PULL_UP)
    lf = Pin(LEFT, Pin.IN, Pin.PULL_UP)
    pir = Pin(PIR, Pin.IN)

    gear = 1
    paused = False
    dz_run = DZ
    lpf_a = LPF_A
    cfg_tag = None
    shots = 0
    shots_mark = 0
    sessions = 0
    present = 0
    was_present = 0
    session_start = 0
    session_s = 0
    last_seen_ms = time.ticks_ms()
    seen_any = False
    sum_gz = 0.0
    sum_gy = 0.0
    pk_gz = 0.0
    tgz = 0
    rec = macros.Recorder()
    play = macros.Player()
    macro_steps = macros.load()
    click_cnt = 0
    click_t = 0
    play_mask = 0
    lz = 0.0
    ly = 0.0
    acc_x = 0.0
    acc_y = 0.0
    last_l = last_r = False
    lf_prev = 1
    lf_down_ms = 0
    still_ms = 0
    n = 0
    rate_t0 = time.ticks_ms()
    t_next = time.ticks_ms()
    lg_gx = lg_gy = lg_gz = 0.0
    lg_rz = lg_ry = 0.0
    moves_sent = 0

    _rl('net ' + netlink.start())
    beep(1, on=400)
    oled.render(gear, 'ACTIVE', 'ready')
    _rl('LOOP START')

    while True:
        l = (up.value() == 0)
        r = (dn.value() == 0)
        changed = False
        if l != last_l:
            gm.left(l)
            last_l = l
            changed = True
            if l:
                shots += 1
            _rl('ev UP -> %s' % l)
        if r != last_r:
            gm.right(r)
            last_r = r
            changed = True
            _rl('ev DOWN -> %s' % r)

        lv = lf.value()
        if lv == 0 and lf_prev == 1:
            lf_down_ms = time.ticks_ms()
        elif lv == 1 and lf_prev == 0:
            h = time.ticks_diff(time.ticks_ms(), lf_down_ms)
            if h >= HOLD_MS:
                paused = not paused
                if paused:
                    gm.release_all()
                    last_l = last_r = False
                lz = ly = 0.0
                acc_x = acc_y = 0.0
                oled.last = None
                changed = True
                beep(1, on=70)
                _rl('ev PAUSE -> %s' % paused)
            elif h < CLICK_MAX_MS:
                click_cnt += 1
                click_t = time.ticks_ms()
        lf_prev = lv
        now_ms = time.ticks_ms()
        if click_cnt and time.ticks_diff(now_ms, click_t) > 450:
            if click_cnt == 1:
                gear = (gear + 1) % len(GEARS)
                oled.last = None
                changed = True
                _rl('ev GEAR -> %d' % (gear + 1))
            elif click_cnt == 2:
                if play.start(macro_steps, now_ms):
                    _rl('ev MACRO PLAY %d steps' % len(macro_steps))
                else:
                    _rl('ev MACRO PLAY - none stored')
            else:
                if rec.active:
                    macro_steps = rec.stop(now_ms)
                    macros.save(macro_steps)
                    _rl('ev MACRO SAVED %d steps' % len(macro_steps))
                else:
                    rec.start(now_ms)
                    _rl('ev MACRO REC START')
            click_cnt = 0
            oled.last = None
        if rec.active:
            rec.feed(now_ms, (1 if l else 0) | (2 if r else 0))
        if play.active:
            pm = play.tick(now_ms)
            if pm is not None and pm != play_mask:
                play_mask = pm
                gm._l = bool(pm & 1)
                gm._r = bool(pm & 2)
                changed = True
        if pir.value():
            last_seen_ms = now_ms
            seen_any = True
        present = 0
        if seen_any and time.ticks_diff(now_ms, last_seen_ms) < PRESENCE_HOLD_MS:
            present = 1
        if present and not was_present:
            session_start = now_ms
            sessions += 1
        was_present = present
        session_s = int(time.ticks_diff(now_ms, session_start) / 1000) if present else 0
        if (now_ms & 0x7F) == 0:
            c = shared.STATE['cfg']
            tag = (c['gear'], c['dz'], c['lp'])
            if tag != cfg_tag:
                cfg_tag = tag
                gear = min(2, max(0, int(c['gear']) - 1))
                dz_run = c['dz'] / 10.0
                k = 2 * 3.14159265 * float(c['lp']) * DT
                lpf_a = k / (k + 1.0)
        if (now_ms & 0xFF) == 0:
            cmdlink.poll()

        gxv, gyv, gzv, tgz = _read(i2c)
        lg_gx = gxv / FS
        lg_gy = gyv / FS
        lg_gz = gzv / FS
        rz = lg_gz - bias_z
        ry = lg_gy - bias_y
        lg_rz = rz
        lg_ry = ry

        if paused:
            rz = 0.0
            ry = 0.0
            lz = ly = 0.0
            acc_x = acc_y = 0.0

        if rz > dz_run:
            rz -= dz_run
        elif rz < -dz_run:
            rz += dz_run
        else:
            rz = 0.0
        if ry > dz_run:
            ry -= dz_run
        elif ry < -dz_run:
            ry += dz_run
        else:
            ry = 0.0

        lz += lpf_a * (rz - lz)
        ly += lpf_a * (ry - ly)
        if rz == 0.0 and -TAIL_DZ < lz < TAIL_DZ:
            lz = 0.0
        if ry == 0.0 and -TAIL_DZ < ly < TAIL_DZ:
            ly = 0.0

        if rz == 0.0 and ry == 0.0 and not paused:
            still_ms += 2
        else:
            still_ms = 0

        gain = GEARS[gear]
        acc_x += -lz * DT * gain
        acc_y += -ly * DT * gain
        sum_gz += lg_gz
        sum_gy += lg_gy
        if abs(lg_gz) > pk_gz:
            pk_gz = abs(lg_gz)

        if changed or acc_x >= 1.0 or acc_x <= -1.0 or acc_y >= 1.0 or acc_y <= -1.0:
            for _ in range(4):
                ix = int(acc_x)
                iy = int(acc_y)
                if ix == 0 and iy == 0:
                    # pending button-state change with no movement: still sent
                    if changed and gm.try_move(0, 0):
                        changed = False
                        moves_sent += 1
                    break
                cx = -127 if ix < -127 else (127 if ix > 127 else ix)
                cy = -127 if iy < -127 else (127 if iy > 127 else iy)
                if not gm.try_move(cx, cy):
                    break
                acc_x -= cx
                acc_y -= cy
                moves_sent += 1
                changed = False

        if oled.last != (gear, 'PAUSED' if paused else 'ACTIVE', 'ready'):
            if paused or still_ms > 300:
                if paused:
                    oled.render(gear, 'PAUSED', 'hold L to resume')
                else:
                    oled.render(gear, 'ACTIVE', 'ready')

        _led_tick()

        n += 1
        t_next = time.ticks_add(t_next, 2)
        dt = time.ticks_diff(t_next, time.ticks_ms())
        if dt > 0:
            time.sleep_ms(dt)
        else:
            t_next = time.ticks_ms()

        now = time.ticks_ms()
        el = time.ticks_diff(now, rate_t0)
        if el >= 2000:
            STATS['rate'] = n * 1000.0 / el
            STATS['sent'] = gm.sent
            STATS['busy'] = gm.busy
            STATS['closed'] = gm.closed
            STATS['bias'] = (bias_x, bias_y, bias_z)
            STATS['cal_sd'] = (sdx, sdy)
            STATS['who'] = who
            STATS['gear'] = gear
            STATS['paused'] = paused
            STATS['moves'] = moves_sent
            _rl('t=%d rate=%.1f sent=%d busy=%d closed=%d moves=%d acc=(%.2f,%.2f) '
                'gz=%.2f gy=%.2f rz=%.2f ry=%.2f lz=%.2f ly=%.2f open=%s' % (
                    now, n * 1000.0 / el, gm.sent, gm.busy, gm.closed, moves_sent,
                    acc_x, acc_y, lg_gz, lg_gy, lg_rz, lg_ry, lz, ly, gm.is_open()))
            _publish(n, sum_gz, sum_gy, pk_gz, tgz, shots, shots_mark, present, session_s, sessions, gear)
            shots_mark = shots
            sum_gz = 0.0
            sum_gy = 0.0
            pk_gz = 0.0
            n = 0
            rate_t0 = now


def _publish(n, sgz, sgy, pk, traw, shots, shots_mark, present, session_s, sessions, gear):
    if n <= 0:
        return
    st = shared.STATE
    mgz = sgz / n
    st['gz'] = mgz
    st['gy'] = sgy / n
    st['gz_peak'] = pk
    st['temp'] = traw / 333.87 + 21.0
    st['shots'] = shots
    st['shots_window'] = shots - shots_mark
    st['present'] = present
    st['session_s'] = session_s
    st['sessions'] = sessions
    st['gear'] = gear + 1
    try:
        smp = st['samples']
        smp.append(min(255, int(abs(mgz))))
        while len(smp) > 30:
            del smp[0]
    except Exception:
        pass
    try:
        import ts_cfg
        if getattr(ts_cfg, 'SERIAL_TELEMETRY', False):
            print('@%.2f|%.2f|%.1f|%d|%d|%d|%.2f' % (
                mgz, sgy / n, traw / 333.87 + 21.0, shots, present, session_s, 0.0))
    except Exception:
        pass


def regs(i2c):
    out = {}
    for r in (0x19, 0x1A, 0x1B, 0x1C, 0x6B, 0x75):
        out['%02X' % r] = i2c.readfrom_mem(MPU, r, 1)[0]
    return out
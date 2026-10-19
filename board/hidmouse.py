# GunMouse HID interface - direct endpoint submit.
#
# We deliberately do NOT use HIDInterface.send_report(): it spins on busy() with
# machine.idle(), and on this firmware that path blew up with
# "TypeError: 'int' object isn't callable" inside /lib/usb/device/hid.py:128.
# We talk to the interrupt endpoint directly instead: check xfer_pending(), then
# submit_xfer(). Zero blocking, zero machine.idle(), and it never raises.
import struct
from usb.device.hid import HIDInterface
from usb.device.mouse import MouseInterface, _MOUSE_REPORT_DESC

_inst = None


class GunMouse(MouseInterface):
    def __init__(self, interval_ms=1):
        HIDInterface.__init__(self, _MOUSE_REPORT_DESC, protocol=0x02,
                              interface_str='Pico Gun Mouse', interval_ms=interval_ms)
        self._l = False
        self._m = False
        self._r = False
        self._buf = bytearray(3)
        self.sent = 0
        self.busy = 0
        self.closed = 0
        self.errs = 0
        self.last_err = None

    def _pack(self, dx, dy):
        b = 0
        if self._l:
            b |= 1
        if self._r:
            b |= 2
        if self._m:
            b |= 4
        struct.pack_into('Bbb', self._buf, 0, b, dx, dy)

    def try_move(self, dx, dy):
        # Non-blocking. False means "not queued - keep the delta".
        if not self.is_open():
            self.closed += 1
            return False
        ep = self._int_ep
        if ep is None:
            self.busy += 1
            return False
        try:
            if self.xfer_pending(ep):
                self.busy += 1
                return False
            self._pack(dx, dy)
            self.submit_xfer(ep, self._buf)
        except Exception as e:
            self.errs += 1
            self.last_err = repr(e)
            self.busy += 1
            return False
        self.sent += 1
        return True

    def kick(self):
        return self.try_move(0, 0)

    def left(self, down):
        self._l = bool(down)

    def right(self, down):
        self._r = bool(down)

    def release_all(self):
        self._l = False
        self._r = False
        self._m = False


def install(interval_ms=1):
    global _inst
    import usb.device
    _inst = GunMouse(interval_ms=interval_ms)
    usb.device.get().init(_inst, builtin_driver=True)
    return _inst


def get():
    return _inst

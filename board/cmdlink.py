"""Downlink command channel over the USB CDC serial link.

The desktop application writes one command per line and the control loop polls for
it, so a profile can be pushed to the board without re-flashing it:

    #CFG <sensitivity gear 1-3> <dead zone x10> <low-pass cutoff Hz>
    #PING

poll() never blocks: if the host is not connected, or nothing has arrived, it
returns immediately and the 500 Hz loop is unaffected.
"""
import sys
import shared

try:
    import uselect as _select
except ImportError:
    try:
        import select as _select
    except ImportError:
        _select = None

_poll = None
_state = 0          # 0 = not tried, 1 = ready, 2 = unavailable
_buf = ""


def _init():
    global _poll, _state
    if _state:
        return _state == 1
    _state = 2
    if _select is None:
        return False
    try:
        _poll = _select.poll()
        _poll.register(sys.stdin, _select.POLLIN)
        _state = 1
        return True
    except Exception:
        _poll = None
        return False


def _apply(parts):
    cfg = shared.STATE["cfg"]
    if len(parts) >= 4:
        try:
            cfg["gear"] = max(1, min(3, int(parts[1])))
            cfg["dz"] = max(0, min(20, int(parts[2])))
            cfg["lp"] = max(10, min(60, int(parts[3])))
        except Exception:
            return False
        print("#ACK CFG %d %d %d" % (cfg["gear"], cfg["dz"], cfg["lp"]))
        return True
    if parts[0] == "PING":
        print("#ACK PONG")
        return True
    return False


def _handle(line):
    if not line.startswith("#"):
        return False
    return _apply(line[1:].split())


def poll():
    """Returns the number of commands applied."""
    global _buf
    if not _init():
        return 0
    n = 0
    try:
        while _poll.poll(0):
            ch = sys.stdin.read(1)
            if not ch:
                break
            if ch == "\n":
                if _handle(_buf.strip()):
                    n += 1
                _buf = ""
            elif len(_buf) < 80:
                _buf += ch
    except Exception:
        pass
    return n

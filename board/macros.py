"""Button macro recorder / player.

A macro is a list of [mask, ms] steps.  mask bit0 = left button, bit1 = right.
Each step means "hold this combination of buttons for ms milliseconds".
macros.json on the flash holds a single macro named "m1".

Recording and playback are driven entirely from the three physical buttons, so no
host link is needed:
  LEFT triple-click  start / stop recording
  LEFT double-click  play the stored macro
  (LEFT single click still cycles sensitivity, hold still pauses)
"""
import time

PATH = "/macros.json"
MAX_STEPS = 200


def _enc(steps):
    return "[" + ",".join("[%d,%d]" % (int(m), int(d)) for m, d in steps) + "]"


def save(steps):
    try:
        f = open(PATH, "w")
        f.write(_enc(steps))
        f.close()
        return True
    except Exception:
        return False


def load():
    try:
        import json
        f = open(PATH)
        txt = f.read()
        f.close()
        data = json.loads(txt)
        out = []
        for step in data:
            out.append([int(step[0]), int(step[1])])
        return out
    except Exception:
        return []


class Recorder(object):
    def __init__(self):
        self.steps = []
        self.t0 = 0
        self.mask = 0
        self.active = False

    def start(self, now):
        self.steps = []
        self.t0 = now
        self.mask = 0
        self.active = True

    def feed(self, now, mask):
        """Call every loop iteration while recording."""
        if not self.active:
            return
        if mask != self.mask:
            dt = time.ticks_diff(now, self.t0)
            if dt > 0:
                self.steps.append([self.mask, dt])
            self.mask = mask
            self.t0 = now
            if len(self.steps) >= MAX_STEPS:
                self.active = False

    def stop(self, now):
        if not self.active:
            return self.steps
        dt = time.ticks_diff(now, self.t0)
        if dt > 0:
            self.steps.append([self.mask, dt])
        self.active = False
        # trailing step must release everything
        self.steps.append([0, 40])
        return self.steps


class Player(object):
    def __init__(self):
        self.steps = []
        self.idx = 0
        self.deadline = 0
        self.active = False

    def start(self, steps, now):
        if not steps:
            return False
        self.steps = steps
        self.idx = 0
        self.deadline = now
        self.active = True
        return True

    def tick(self, now):
        """Returns the button mask to apply, or None when finished."""
        if not self.active:
            return None
        if time.ticks_diff(now, self.deadline) < 0:
            return self.last_mask()
        if self.idx >= len(self.steps):
            self.active = False
            return 0
        m, dur = self.steps[self.idx]
        self.idx += 1
        self.deadline = time.ticks_add(now, max(10, int(dur)))
        self._mask = m
        return m

    def last_mask(self):
        return getattr(self, "_mask", 0)

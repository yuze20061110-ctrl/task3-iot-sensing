import sys, os, time
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QFrame, QVBoxLayout,
                             QHBoxLayout, QStackedWidget, QSizePolicy, QPushButton, QDialog, QComboBox)

import tokens as T
import ui
import data as datamod
import i18n

L = i18n.L
from ui import (PaintWidget, IconButton, Text, Card, NavTab, SubNavItem, Divider,
                SliderRow, Sparkline, StatTile, app_font, rgba,
                i_gear, i_user, i_desktop, i_grid, i_list, i_crosshair,
                i_logo, i_back, i_battery)

HERE = os.path.dirname(os.path.abspath(__file__))

# The live telemetry channel.  Leave the dictionary empty to fall back to the
# synthetic source, which keeps the interface usable with no network at all.
THINGSPEAK = {"channel": "3541064", "read_key": "35YX48TUIJDYNUQ6"}


def default_source():
    """Prefer the device on USB, then the cloud channel, then synthetic data."""
    port = datamod.find_pico_port()
    if port:
        return datamod.make_source("serial", port=port)
    if THINGSPEAK.get("channel") and THINGSPEAK.get("read_key"):
        return datamod.make_source("cloud", **THINGSPEAK)
    return datamod.make_source("mock")


# ============ device card ============

class DeviceCard(ui.Card):
    clicked = None

    def __init__(self, parent=None):
        super().__init__(T.RADIUS_LG, T.SURFACE, parent)
        self.setFixedSize(T.CARD_W, T.CARD_H)
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(T.CARD_PAD, 30, T.CARD_PAD, 0)
        lay.setSpacing(0)

        name = Text("PICO GUN\nMOUSE", 19.0, True)
        name.setWordWrap(True)
        name.setMaximumHeight(160)
        lay.addWidget(name)

        lay.addSpacing(10)
        row = QWidget(); row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row); rl.setContentsMargins(0, 2, 0, 0); rl.setSpacing(T.GAP_STATUS)
        self.pct_lb = Text("100%", 9.5, True, T.ON_BG_MED)
        rl.addWidget(self.pct_lb)
        rl.addWidget(PaintWidget(i_battery, 20, 16))
        rl.addSpacing(4)
        self.vsys_lb = Text("4.9 V", 9.0, False, T.ON_BG_LOW)
        self.pir_lb = Text("PIR", 9.0, False, T.ON_BG_LOW)
        for lb in (self.vsys_lb, self.pir_lb):
            lb.setContentsMargins(0, 0, 4, 0)
            rl.addWidget(lb)
        rl.addStretch(1)
        lay.addWidget(row)

        lay.addSpacing(12)
        thumb = QLabel()
        thumb.setStyleSheet("background:transparent;")
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setMinimumHeight(T.THUMB_MIN)
        p = os.path.join(HERE, "device_card.png")
        if os.path.exists(p):
            thumb.setPixmap(QPixmap(p).scaled(QSize(200, 168), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(thumb, 1)

        foot = QWidget(); foot.setFixedHeight(T.FOOTER_H); foot.setStyleSheet("background:transparent;")
        fl = QHBoxLayout(foot); fl.setContentsMargins(0, 0, -8, 8)
        fl.addStretch(1)
        fl.addWidget(IconButton(i_crosshair, 40))
        lay.addWidget(foot)

    def set_status(self, d):
        v = d.get("vsys") or 0.0
        self.vsys_lb.setText(("%.1f V" % v) if v > 0.5 else "USB")
        self.pir_lb.setText("PIR ●" if d.get("present") else "PIR ○")

    def mousePressEvent(self, e):
        if self.clicked:
            self.clicked()


# ============ top-level pages ============

class DevicesPage(QWidget):
    def __init__(self, on_open=None):
        super().__init__()
        self.card = DeviceCard(self)
        body = QHBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.addStretch(1)
        body.addWidget(self.card)
        body.addStretch(1)
        self.card.clicked = on_open
        self.tg1 = IconButton(i_grid, 44, 32, self)
        self.tg2 = IconButton(i_list, 44, 32, self)

    def update_data(self, d):
        self.card.set_status(d)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.tg2.move(self.width() - 26 - 44, 26)
        self.tg1.move(self.width() - 26 - 44 - 48, 26)


class PageTitle(QWidget):
    def __init__(self, title, sub="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(Text(title, 17.0, True))
        if sub:
            lay.addWidget(Text(sub, 9.5, False, T.ON_BG_LOW))


class SessionsPage(QWidget):
    """A log of real usage periods, built from the infrared presence flag."""

    def __init__(self, log=None):
        super().__init__()
        self.log = log
        self._shown = -1
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 26, 34, 24)
        lay.setSpacing(16)
        lay.addWidget(PageTitle(L("Sessions"), L("Every engagement the infrared sensor recorded")))

        tiles = QHBoxLayout(); tiles.setSpacing(12)
        self.t_sess = StatTile(L("Sessions today"), "-", L("decided by the PIR sensor"))
        self.t_shots = StatTile(L("Total shots"), "-", L("trigger presses"))
        self.t_peak = StatTile(L("Peak rate"), "-", L("range +/-2000 dps"))
        self.t_temp = StatTile(L("Die temperature"), "-", L("on the MPU-6050"))
        for t in (self.t_sess, self.t_shots, self.t_peak, self.t_temp):
            t.setFixedHeight(84)
            tiles.addWidget(t)
        lay.addLayout(tiles)

        self.card = Card(T.RADIUS_LG, T.SURFACE)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(0, 8, 0, 8)
        self.body.setSpacing(0)
        lay.addWidget(self.card, 1)

        self.empty = Text(L("No usage recorded yet"), 10.5, False, T.ON_BG_LOW)
        self.empty.setAlignment(Qt.AlignCenter)

    def _header(self):
        head = QWidget(); hl = QHBoxLayout(head)
        hl.setContentsMargins(20, 6, 20, 10)
        for w, s in ((150, L("Start")), (110, L("Duration")), (90, L("Shots")),
                     (110, L("Peak rate")), (0, L("Intensity"))):
            lb = Text(s, 9.0, False, T.ON_BG_LOW)
            if w:
                lb.setFixedWidth(w)
            hl.addWidget(lb)
        hl.addStretch(1)
        return head

    def _row(self, start_s, dur_s, shots, peak, level):
        rw = QWidget(); rl = QHBoxLayout(rw)
        rl.setContentsMargins(20, 10, 20, 10)
        for w, s in ((150, start_s), (110, dur_s), (90, str(shots)), (110, peak)):
            lb = Text(s, 10.0, False, T.ON_BG)
            lb.setFixedWidth(w)
            rl.addWidget(lb)
        col = {"High": T.ERROR, "Medium": T.WARN, "Low": T.SUCCESS}[level]
        chip = QLabel(L(level))
        chip.setAlignment(Qt.AlignCenter)
        chip.setFixedSize(52, 20)
        chip.setFont(app_font(9.0, True))
        chip.setStyleSheet("color:%s;background:%s;border-radius:4px;"
                           % (col, rgba(col, 0.16).name(QColor.HexArgb)))
        rl.addWidget(chip)
        rl.addStretch(1)
        return rw

    def _rebuild(self, rows):
        while self.body.count():
            it = self.body.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
        self.body.addWidget(self._header())
        self.body.addWidget(Divider())
        if not rows:
            self.body.addWidget(self.empty)
            self.body.addStretch(1)
            return
        for i, r in enumerate(rows):
            start = time.strftime("%H:%M", time.localtime(r.get("start", 0)))
            dur = int(r.get("dur") or 0)
            dur_s = "%02d:%02d" % (dur // 60, dur % 60)
            shots = int(r.get("shots") or 0)
            rate = int(shots * 60 / dur) if dur else shots
            level = "High" if rate >= 20 else ("Medium" if rate >= 8 else "Low")
            self.body.addWidget(self._row(start, dur_s, shots, "%d /min" % rate, level))
            if i < len(rows) - 1:
                self.body.addWidget(Divider())
        self.body.addStretch(1)

    def update_data(self, d):
        rows = self.log.live() if self.log is not None else []
        n = len(rows)
        shots = sum(int(r.get("shots") or 0) for r in rows)
        self.t_sess.set_value("%d" % n if i18n.current() == "zh" else "%d session%s" % (n, "" if n == 1 else "s"))
        self.t_shots.set_value("%d" % shots)
        rates = [int(r.get("shots") or 0) * 60 / max(1, int(r.get("dur") or 1)) for r in rows]
        self.t_peak.set_value("%d /min" % (max(rates) if rates else 0))
        self.t_temp.set_value("%.1f \u00b0C" % (d.get("temp") or 0))
        if n != self._shown:
            self._shown = n
            self._rebuild(rows)

class ChannelWorker(QThread):
    """Polls the ThingSpeak channel so the Cloud page shows a live link."""

    done = pyqtSignal(object)

    def __init__(self, probe, every=5.0, parent=None):
        super().__init__(parent)
        self.probe = probe
        self.every = every
        self._stop = False

    def run(self):
        while not self._stop:
            try:
                self.done.emit(self.probe.check())
            except Exception as e:
                self.done.emit({'ok': False, 'code': 0, 'ms': 0, 'rows': 0,
                                'last_at': '', 'err': repr(e)})
            for _ in range(int(self.every * 10)):
                if self._stop:
                    return
                self.msleep(100)

    def stop(self):
        self._stop = True

class CloudPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 26, 34, 24)
        lay.setSpacing(16)
        lay.addWidget(PageTitle(L("Cloud"), L("ThingSpeak channel · uplink telemetry and downlink commands")))

        tiles = QHBoxLayout(); tiles.setSpacing(12)
        self.t_state = StatTile(L("Channel"), THINGSPEAK["channel"], "ThingSpeak")
        self.t_link = StatTile(L("Link"), "-", L("checked every 5 s"))
        self.t_ms = StatTile(L("Latency"), "-", L("round trip to the channel"))
        self.t_up = StatTile(L("Records"), "-", L("entries on the channel"))
        self.t_last = StatTile(L("Last record"), "-", L("UTC timestamp"))
        for t in (self.t_state, self.t_link, self.t_ms, self.t_up, self.t_last):
            t.setFixedHeight(84)
            tiles.addWidget(t)
        lay.addLayout(tiles)

        self.probe = datamod.ChannelProbe(THINGSPEAK["channel"], THINGSPEAK["read_key"])
        self.worker = ChannelWorker(self.probe, 5.0, self)
        self.worker.done.connect(self._on_probe)
        self.worker.start()

        body = QHBoxLayout(); body.setSpacing(12)

        left = Card(T.RADIUS_LG, T.SURFACE)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 16, 20, 16)
        ll.setSpacing(10)
        ll.addWidget(Text(L("Field map"), 11.0, True))
        for f, name in (("field1", "Yaw rate gz (dps)"), ("field2", "Pitch rate gy (dps)"),
                        ("field3", "Temperature (°C)"), ("field4", "Trigger count"),
                        ("field5", "Operator present (0/1)"), ("field6", "Session length (s)"),
                        ("field7", "Supply voltage (V)"), ("field8", "Packed waveform (base64)")):
            rw = QWidget(); rl = QHBoxLayout(rw)
            rl.setContentsMargins(0, 0, 0, 0)
            k = Text(f, 9.5, True, T.PRIMARY); k.setFixedWidth(58)
            rl.addWidget(k)
            rl.addWidget(Text(L(name), 9.5, False, T.ON_BG))
            rl.addStretch(1)
            ll.addWidget(rw)
        ll.addStretch(1)
        body.addWidget(left, 1)

        right = Card(T.RADIUS_LG, T.SURFACE)
        rl2 = QVBoxLayout(right)
        rl2.setContentsMargins(20, 16, 20, 16)
        rl2.setSpacing(10)
        rl2.addWidget(Text(L("Yaw rate history (field 1)"), 11.0, True))
        sp = Sparkline(color=T.SECONDARY)
        sp.clear()
        self.sp_rssi = sp
        rl2.addWidget(sp, 1)
        rl2.addWidget(Text(L("one point per record, oldest on the left"), 9.0, False, T.ON_BG_LOW))
        body.addWidget(right, 1)

        lay.addLayout(body, 1)

    def _on_probe(self, res):
        if res.get("ok"):
            code = res.get("code") or 0
            self.t_link.set_value(("200 OK" if code == 200 else str(code)))
            self.t_ms.set_value("%d ms" % res.get("ms", 0))
            self.t_up.set_value("%d" % (res.get("rows") or 0))
            at = res.get("last_at") or ""
            self.t_last.set_value(at[11:19] + " UTC" if len(at) > 18 else "-")
        else:
            self.t_link.set_value(L("unreachable"))
            self.t_ms.set_value("%d ms" % res.get("ms", 0))

    def stop(self):
        try:
            self.worker.stop()
            self.worker.wait(1500)
        except Exception:
            pass

    def update_data(self, d):
        self.sp_rssi.push(float(d.get("gz") or 0.0))


class ProtoButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(30)
        self.setFont(app_font(9.5, True))
        self.setStyleSheet(
            "QPushButton{color:%s;background:%s;border:none;border-radius:%dpx;}"
            "QPushButton:hover{background:%s;}"
            "QPushButton:pressed{background:%s;}"
            % (T.ON_BG, T.SURFACE_2, T.RADIUS, T.SURFACE_3, T.PRIMARY))


class ProfilesPage(QWidget):
    DATA = [
        ("Default", "18 c/deg · 0.4 dps dead zone · 35 Hz cutoff", True, "#CFG 2 4 35"),
        ("Precision", "9 c/deg · 0.3 dps dead zone · 25 Hz cutoff", False, "#CFG 1 3 25"),
        ("Flick", "36 c/deg · 0.6 dps dead zone · 45 Hz cutoff", False, "#CFG 3 6 45"),
    ]

    def __init__(self, on_send=None):
        self.on_send = on_send
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 26, 34, 24)
        lay.setSpacing(16)
        lay.addWidget(PageTitle(L("Profiles"), L("Local JSON · pushed to the device, mirrored to the cloud")))

        grid = QHBoxLayout(); grid.setSpacing(12)
        for name, desc, active, cmd in self.DATA:
            c = Card(T.RADIUS_LG, T.SURFACE)
            c.setFixedHeight(150)
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 16, 18, 14)
            cl.setSpacing(8)
            top = QHBoxLayout(); top.setContentsMargins(0, 0, 0, 0)
            top.addWidget(Text(L(name), 12.0, True))
            top.addStretch(1)
            if active:
                chip = QLabel(L("In use"))
                chip.setAlignment(Qt.AlignCenter)
                chip.setFixedSize(52, 20)
                chip.setFont(app_font(9.0, True))
                chip.setStyleSheet("color:%s;background:%s;border-radius:4px;"
                                   % (T.PRIMARY, rgba(T.PRIMARY, 0.16).name(QColor.HexArgb)))
                top.addWidget(chip)
            cl.addLayout(top)
            cl.addWidget(Text(L(desc), 9.5, False, T.ON_BG_MED))
            cl.addStretch(1)
            btn = ProtoButton(L("Send to device"))
            btn.clicked.connect(lambda _=False, c=cmd: self.on_send and self.on_send(c))
            cl.addWidget(btn)
            grid.addWidget(c)
        grid.addStretch(1)
        lay.addLayout(grid)
        lay.addStretch(1)


# ============ device detail ============

class DeviceDetailPage(QWidget):
    GEARS = {1: 9, 2: 18, 3: 36}

    def __init__(self, on_back=None, on_config=None):
        super().__init__()
        self.on_back = on_back
        self.on_config = on_config
        self._cfg = {"gear": 2, "dz": 4, "lp": 35}
        self._syncing = False
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QWidget()
        side.setFixedWidth(T.SIDEBAR_W)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(18, 26, 12, 20)
        sl.setSpacing(2)
        back = QWidget(); bl = QHBoxLayout(back)
        bl.setContentsMargins(0, 0, 0, 14); bl.setSpacing(9)
        bb = IconButton(i_back, 26, 26)
        if on_back:
            bb.clicked.connect(on_back)
        bl.addWidget(bb)
        bl.addWidget(Text(L("Back to devices"), 9.5, False, T.ON_BG_MED))
        bl.addStretch(1)
        sl.addWidget(back)

        self.items = []
        for i, n in enumerate(("Sensitivity", "Assignments", "Lighting", "Device settings", "About")):
            it = SubNavItem(n, active=(i == 0))
            self.items.append(it)
            sl.addWidget(it)
        sl.addStretch(1)
        root.addWidget(side)

        body = QWidget()
        bl2 = QVBoxLayout(body)
        bl2.setContentsMargins(8, 26, 34, 24)
        bl2.setSpacing(14)
        bl2.addWidget(PageTitle(L("Sensitivity"), L("DpiPanel · gain, dead zone and filtering")))

        panel = Card(T.RADIUS_LG, T.SURFACE)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(22, 18, 22, 18)
        pl.setSpacing(16)
        pl.addWidget(Text(L("Gain curve"), 11.0, True))
        self.sl_gear = SliderRow(L("Sensitivity (counts / degree)"), 1, 3, 2, "",
                                 self._changed, self._gear_text)
        self.sl_dz = SliderRow(L("Soft dead zone (dps x 10)"), 0, 20, 4, "", self._changed)
        self.sl_lp = SliderRow(L("Low-pass cutoff (Hz)"), 10, 60, 35, " Hz", self._changed)
        for w in (self.sl_gear, self.sl_dz, self.sl_lp):
            pl.addWidget(w)
        bl2.addWidget(panel)

        canvas = Card(T.RADIUS_LG, T.SURFACE)
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(22, 16, 22, 16)
        cl.setSpacing(8)
        cl.addWidget(Text(L("Live angular rate (DpiCanvas)"), 11.0, True))
        sp = Sparkline(color=T.PRIMARY)
        sp.clear()
        self.sp_live = sp
        cl.addWidget(sp, 1)
        bl2.addWidget(canvas, 1)
        root.addWidget(body, 1)

    def _gear_text(self, v):
        return "%d c/deg" % self.GEARS.get(int(v), 18)

    def _changed(self, _v=None):
        if self._syncing:
            return
        self._cfg = {"gear": self.sl_gear.get_value(),
                     "dz": self.sl_dz.get_value(),
                     "lp": self.sl_lp.get_value()}
        if self.on_config:
            self.on_config(self._cfg["gear"], self._cfg["dz"], self._cfg["lp"])

    def set_config(self, gear, dz, lp):
        """Reflect the values the device reported, without echoing them back."""
        self._syncing = True
        try:
            self.sl_gear.set_value(gear)
            self.sl_dz.set_value(dz)
            self.sl_lp.set_value(lp)
            self._cfg = {"gear": int(gear), "dz": int(dz), "lp": int(lp)}
        finally:
            self._syncing = False

    def update_data(self, d):
        self.sp_live.push(float(d.get("gz") or 0.0))


# ============ shell ============

class SettingsDialog(QDialog):
    """The only setting that changes the whole window is the language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(L("Settings"))
        self.setModal(True)
        self.setFixedWidth(360)
        self.setStyleSheet("QDialog{background:%s;} QLabel{color:%s;}"
                           % (T.SURFACE, T.ON_BG))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)

        head = QLabel(L("Interface language"))
        head.setFont(app_font(10.5, True))
        lay.addWidget(head)

        self.box = QComboBox()
        self.box.setFont(app_font(10.0))
        self.box.setStyleSheet(
            "QComboBox{color:%s;background:%s;border:1px solid %s;"
            "border-radius:6px;padding:6px 10px;}"
            % (T.ON_BG, T.SURFACE_2, T.OUTLINE))
        for code, label in i18n.LANGS:
            self.box.addItem(label, code)
        cur = i18n.current()
        self.box.setCurrentIndex(0 if cur == "en" else 1)
        lay.addWidget(self.box)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = ProtoButton(L("Cancel"))
        cancel.clicked.connect(self.reject)
        ok = ProtoButton(L("Apply"))
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def choice(self):
        return self.box.currentData()


class Header(QWidget):
    def __init__(self, on_nav, on_settings=None):
        super().__init__()
        self.setFixedHeight(T.HEADER_H)
        self.setStyleSheet("background:%s;" % T.BG)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 0, 18, 0)
        lay.setSpacing(0)
        lay.addWidget(PaintWidget(i_logo, 40, 40))
        lay.addSpacing(56)
        self.tabs = []
        for i, n in enumerate(("Devices", "Sessions", "Cloud", "Profiles")):
            t = NavTab(n, active=(i == 0))
            t.clicked.connect(on_nav)
            self.tabs.append(t)
            lay.addWidget(t)
            lay.addSpacing(24)
        lay.addStretch(1)

        pill = QFrame()
        pill.setFixedHeight(38)
        pill.setStyleSheet("QFrame{background:%s;border-radius:%dpx;}" % (T.SURFACE, T.RADIUS))
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(12, 0, 16, 0)
        pl.setSpacing(9)
        pl.addWidget(PaintWidget(i_desktop, 26, 26))
        pl.addWidget(Text(L("Desktop: Default"), 10.0))
        lay.addWidget(pill)
        lay.addSpacing(16)
        gear = IconButton(i_gear, 34)
        if on_settings:
            gear.clicked.connect(on_settings)
        lay.addWidget(gear)
        lay.addSpacing(2)
        lay.addWidget(IconButton(i_user, 34))

    def set_active(self, name):
        for t in self.tabs:
            t.set_active(t.name == name)


class StatusBar(QWidget):
    def __init__(self, text):
        super().__init__()
        self.setFixedHeight(T.STATUS_H)
        self.setStyleSheet("background:%s;" % T.STATUSBAR)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)
        self.pres = Text(L("PIR") + " \u25cb", 10.0, True, T.ON_BG_LOW)
        self.pres.setFixedWidth(58)
        lay.addWidget(self.pres)
        self.lb = Text(text, 10.0)
        self.lb.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lb, 1)
        self._on = None

    def set_text(self, t):
        self.lb.setText(t)

    def set_presence(self, on):
        on = bool(on)
        if on == self._on:
            return
        self._on = on
        self.pres.setText(L("PIR") + (" \u25cf" if on else " \u25cb"))
        self.pres.setStyleSheet("color:%s;" % (T.SUCCESS if on else T.ON_BG_LOW))


class Poller(QThread):
    """Runs source.poll() off the GUI thread.

    The ThingSpeak source performs a blocking HTTPS request inside poll().  Calling
    it from the timer callback froze the window for the length of the request, which
    is what made the interface feel slow.  The worker owns the poll and hands the
    result back through a signal, so the event loop never waits on the network.
    """

    done = pyqtSignal(object)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self._stop = False

    def run(self):
        while not self._stop:
            try:
                d = self.source.poll()
                self.done.emit(d or {})
            except Exception as e:
                self.done.emit({"_error": repr(e)})
            for _ in range(10):
                if self._stop:
                    return
                self.msleep(100)

    def stop(self):
        self._stop = True


class Sender(QThread):
    """One-shot worker for a profile write, which is also a network request."""

    done = pyqtSignal(str, str)

    def __init__(self, source, cmd, parent=None):
        super().__init__(parent)
        self.source = source
        self.cmd = cmd

    def run(self):
        try:
            res = self.source.send(self.cmd)
        except Exception as e:
            res = "send failed: %r" % (e,)
        self.done.emit(self.cmd, res)


class MainWindow(QWidget):
    def __init__(self, source=None):
        super().__init__()
        self.setWindowTitle("PICO GUN MOUSE Studio")
        self.resize(1030, 768)
        self.setAttribute(Qt.WA_StyledBackground, False)

        self.session_log = datamod.SessionLog()
        self.detail = DeviceDetailPage(on_back=self.close_detail,
                                       on_config=self.send_config)
        self.stack = QStackedWidget()
        self.pages = {
            "Devices": DevicesPage(on_open=self.open_detail),
            "Sessions": SessionsPage(log=self.session_log),
            "Cloud": CloudPage(),
            "Profiles": ProfilesPage(on_send=self.send_profile),
        }
        order = ("Devices", "Sessions", "Cloud", "Profiles")
        for k in order:
            self.stack.addWidget(self.pages[k])

        self.source = source if source is not None else default_source()
        self.header = Header(self.on_nav, self.open_settings)
        self.status = StatusBar(L("source: %s") % self.source.name)
        self.poller = Poller(self.source, self)
        self.poller.done.connect(self._apply)
        self.poller.start()
        if self.source.name != "serial":
            self.watchdog = QTimer(self)
            self.watchdog.timeout.connect(self._watch_source)
            self.watchdog.start(3000)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.header)
        self.content = QStackedWidget()
        self.content.addWidget(self.stack)
        self.content.addWidget(self.detail)
        root.addWidget(self.content, 1)
        root.addWidget(self.status)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            code = dlg.choice()
            if code != i18n.current():
                i18n.set_lang(code)
                self.restart = True
                self.close()

    def _watch_source(self):
        """Switch to the board as soon as it is plugged in."""
        if self.source.name == "serial":
            self.watchdog.stop()
            return
        port = datamod.find_pico_port()
        if not port:
            return
        self.watchdog.stop()
        try:
            self.poller.stop()
            self.poller.wait(1500)
        except Exception:
            pass
        self.source = datamod.make_source("serial", port=port)
        self.status.set_text(L("source: %s") % self.source.name)
        self.poller = Poller(self.source, self)
        self.poller.done.connect(self._apply)
        self.poller.start()

    def send_config(self, gear, dz, lp):
        self.send_profile("#CFG %d %d %d" % (gear, dz, lp))

    def send_profile(self, cmd):
        self.status.set_text("%s  →  sending" % (cmd,))
        self._sender = Sender(self.source, cmd, self)
        self._sender.done.connect(self._on_sent)
        self._sender.start()

    def _on_sent(self, cmd, res):
        self.status.set_text("%s  →  %s" % (cmd, res))
        self.profile_flash = res

    def _tick(self):
        """One synchronous poll.  Kept for the screenshot scripts only; the running
        application uses the Poller thread so the window never waits on the network."""
        try:
            d = self.source.poll()
        except Exception as e:
            self.status.set_text(L("source error: %r") % (e,))
            return
        self._apply(d or {})

    def _apply(self, d):
        try:
            self.session_log.update(d)
        except Exception:
            pass
        note = getattr(self.source, "note", "") or ""
        if note.startswith("device: CFG"):
            p = note.split()
            if len(p) >= 5:
                try:
                    self.detail.set_config(int(p[2]), int(p[3]), int(p[4]))
                except Exception:
                    pass
        if d.get("_error"):
            self.status.set_text(L("source error: %s") % (d["_error"],))
            return
        if not d:
            self.status.set_text("%s  ·  %s" % (self.source.name, self.source.note))
            return
        self.status.set_presence(d.get("present"))
        self.status.set_text(
            "%s  \u00b7  \u0394gz %+.1f dps  \u00b7  %.1f\u00b0C  \u00b7  %d shots  \u00b7  %s"
            % (self.source.name, d.get("gz", 0.0), d.get("temp", 0.0),
               d.get("shots", 0), self.source.note))
        w = self.content.currentWidget()
        if w is self.stack:
            w = self.stack.currentWidget()
        fn = getattr(w, "update_data", None)
        if fn:
            try:
                fn(d)
            except Exception as e:
                self.status.set_text(L("update_data failed: %r") % (e,))

    def closeEvent(self, e):
        try:
            self.pages["Cloud"].stop()
        except Exception:
            pass
        try:
            self.poller.stop()
            self.poller.wait(1500)
        except Exception:
            pass
        super().closeEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(T.BG))
        p.end()

    def on_nav(self, name):
        self.header.set_active(name)
        self.content.setCurrentIndex(0)
        self.stack.setCurrentWidget(self.pages[name])

    def open_detail(self):
        self.header.set_active("Devices")
        self.content.setCurrentWidget(self.detail)

    def close_detail(self):
        self.content.setCurrentIndex(0)

    def show_page(self, name):
        self.on_nav(name)


def main():
    qa = QApplication(sys.argv)
    i18n.load()
    # the window is rebuilt once when the language changes, so every label is
    # re-created through L() with the new language in effect
    while True:
        w = MainWindow()
        w.restart = False
        w.show()
        qa.exec_()
        if not w.restart:
            break


if __name__ == "__main__":
    main()